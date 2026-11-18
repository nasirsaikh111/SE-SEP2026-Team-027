"""Sangam AI services (advisory only). Django glue around the framework-free core in apps.assistant_ai.ml.

- AI never approves, rejects or creates anything. Only mentoring.services.approve_match() creates a mentorship.
- Every feature has a rule-based fallback when the embedding model or the LLM is unavailable.
- No email / phone / roll number is ever sent to a model or returned in an AI response.
"""
import logging
import re
from datetime import timedelta

from django.conf import settings
from django.db.models import Count, Avg, Q, Max, F
from django.utils import timezone

from apps.accounts.models import MentorProfile, StudentProfile
from apps.mentoring.models import (Mentorship, MentoringRequest, AvailabilityCheck, Meeting, Feedback, Goal, Outcome, Alert)

from . import llm
from .ml import matching, priority as prio, dropoff, summary as summ, retrieval
from .ml.embeddings import MiniLMEmbedder, CallableEmbedder, EmbeddingUnavailable
from .ml.text import strip_pii, cap_words, contains_pii

logger = logging.getLogger(__name__)
_EMBEDDER = {}


# ------------------------------------------------------------------ embeddings
# Picks the embedding backend from settings; tests swap this for a mock
def get_embedder():
    """Embedder from settings, or None (rule-based fallback). Tests patch this function."""
    backend = getattr(settings, 'SANGAM_EMBEDDING_BACKEND', 'none')
    if backend == 'none':
        return None
    if backend not in _EMBEDDER:
        if backend == 'gemini':
            _EMBEDDER[backend] = CallableEmbedder(llm.embed, 'gemini-embedding')
        else:
            _EMBEDDER[backend] = MiniLMEmbedder(settings.SANGAM_EMBEDDING_MODEL, settings.SANGAM_EMBEDDING_TIMEOUT_SECONDS)
    return _EMBEDDER[backend]


def ollama_reply(messages):
    """Backwards-compatible helper: messages -> text via the configured provider (or None)."""
    system = '\n'.join(m['content'] for m in messages if m['role'] == 'system') or None
    user = '\n'.join(m['content'] for m in messages if m['role'] != 'system')
    return llm.generate(user, system=system)


# ------------------------------------------------------------------ KAN-46 matching
# Hard filters run in the database before any scoring
def eligible_mentors(request_obj):
    """Hard filters: verified, available, discoverable, active MENTOR user, no active mentorship,
    no pending availability check for this same request."""
    busy = Mentorship.objects.filter(status='ACTIVE').values_list('mentor_id', flat=True)
    pending = AvailabilityCheck.objects.filter(request=request_obj, status='PENDING').values_list('mentor_id', flat=True)
    return (MentorProfile.objects.filter(user__role='MENTOR', user__is_active=True, is_verified=True, is_available=True,
                                         is_discoverable=True)
            .exclude(user_id__in=busy).exclude(user_id__in=pending).select_related('user').order_by('user_id'))


def _mentor_dict(p):
    return {'id': p.user_id, 'domain': p.domain, 'specialty': p.specialty, 'skills': p.skills or [],
            'career_path': p.career_path, 'experience_years': p.experience_years, 'bio': p.bio or ''}


# Personal details are stripped from the statement before it is embedded
def _request_dict(r):
    clean, _ = strip_pii(r.problem_statement)
    return {'id': r.pk, 'domain': r.domain, 'pathway': r.pathway, 'problem_statement': clean,
            'preferred_mentor_id': r.preferred_mentor_id}


# Score mentors, then add display fields; never include email or phone
def ranked_candidates(request_obj, limit=5):
    """Returns (candidates, algorithm, semantic_used). Deterministic; ties broken by mentor id."""
    profiles = list(eligible_mentors(request_obj))
    by_id = {p.user_id: p for p in profiles}
    emb = get_embedder()
    weights = getattr(settings, 'SANGAM_MATCH_WEIGHTS', None)
    try:
        res, algo, sem = matching.rank(_request_dict(request_obj), [_mentor_dict(p) for p in profiles], weights, emb, k=limit)
    except EmbeddingUnavailable:
        res, algo, sem = matching.rank(_request_dict(request_obj), [_mentor_dict(p) for p in profiles], weights, None, k=limit)
    out = []
    for c in res:
        p = by_id[c['mentor_id']]
        u = p.user
        name = (u.first_name or '').strip() or 'Alumni mentor'
        headline = ' at '.join(x for x in (p.current_role, p.company) if x)
        out.append({'mentor_id': p.user_id, 'name': name, 'headline': headline, 'domain': p.domain, 'specialty': p.specialty,
                    'experience_years': p.experience_years, 'score': c['score'], 'reasons': c['reasons'],
                    'features': c['features']})
    return out, algo, sem


# Optional friendlier wording from the LLM; the order never changes
def explain_candidates(request_obj, candidates, top_n=5):
    """Optionally rephrase template reasons into one friendly sentence. Ranking is never changed."""
    used = False
    template = summ.load_prompt('explain_v1')
    for c in candidates[:top_n]:
        text = llm.generate(template.replace('{{REASONS}}', '; '.join(c['reasons'])), timeout=8)
        if text:
            c['explanation'] = re.sub(r'\s+', ' ', text).strip()[:240]
            used = True
        else:
            c['explanation'] = '; '.join(c['reasons'])
    return candidates[:top_n], used


# Full suggestion flow: rank, explain, write the audit row
def suggest_mentors(request_obj, requested_by, k=5, explain=True):
    from .models import MatchSuggestionAudit
    cands, algo, sem = ranked_candidates(request_obj, limit=k)
    used_llm = False
    if explain and llm.provider() != 'none':
        cands, used_llm = explain_candidates(request_obj, cands, top_n=k)
    else:
        for c in cands:
            c['explanation'] = '; '.join(c['reasons'])
    MatchSuggestionAudit.objects.create(request=request_obj, requested_by=requested_by, algorithm=algo,
                                        candidate_count=len(cands), used_local_llm=used_llm)
    return {'request_id': request_obj.pk, 'algorithm': algo, 'embedding_model_used': sem, 'fallback': not sem,
            'fallback_reason': None if sem else 'embedding model unavailable or disabled; rule-based ranking used',
            'llm_explanations_used': used_llm, 'k': k, 'candidates': cands,
            'advisory_only': True, 'approval_required': True, 'student_cannot_choose': True}


# ------------------------------------------------------------------ request priority
# Advisory priority; IIC can override it with a reason
def assess_request_priority(request_obj, save=True):
    from .models import AIRequestAssessment
    level = getattr(getattr(request_obj.student, 'student_profile', None), 'level', '')
    withdrawals = MentoringRequest.objects.filter(student=request_obj.student, status='WITHDRAWN').exclude(pk=request_obj.pk).count()
    days = (timezone.now() - request_obj.submitted_at).days
    f = prio.extract_features(request_obj.problem_statement, days, level, withdrawals)
    r = prio.score(f, getattr(settings, 'SANGAM_PRIORITY_WEIGHTS', None))
    if not save:
        return r
    return AIRequestAssessment.objects.create(request=request_obj, suggested_priority=r['priority'], explanation=r['explanation'][:500],
                                              confidence=r['confidence'], factors=r['factors'], algorithm=prio.ALGORITHM)


def assessment_json(a):
    return {'request_id': a.request_id, 'assessment_id': a.pk, 'suggested_priority': a.suggested_priority,
            'effective_priority': a.effective_priority, 'explanation': a.explanation, 'confidence': a.confidence,
            'factors': a.factors, 'algorithm': a.algorithm, 'override_priority': a.override_priority or None,
            'override_reason': a.override_reason or None, 'overridden_by': a.overridden_by_id,
            'overridden_at': a.overridden_at, 'created_at': a.created_at, 'advisory_only': True}


# ------------------------------------------------------------------ KAN-57 summaries
def known_names_for(mentorship):
    names = []
    for u in (mentorship.student, mentorship.mentor):
        full = f'{u.first_name} {u.last_name}'.strip()
        if full:
            names.append(full)
    return names


# Clean the notes, ask the LLM, validate, retry once, else use the extractive draft
def summarise_notes(notes, known_names=()):
    """Returns (draft dict, status) where status in ok | fallback | timeout. Nothing is stored here."""
    clean, counts = strip_pii(notes, known_names)
    clean, truncated = cap_words(clean, 2000)
    base = {'prompt_version': summ.PROMPT_VERSION, 'pii_removed': counts, 'input_truncated': truncated}
    prompt = summ.build_prompt(clean)
    timed_out = False
    for _ in range(2):  # one retry on invalid JSON
        r = llm.generate_detailed(prompt, retries=0)
        if r.error == 'timeout':
            timed_out = True
            break
        if r.text is None:
            break
        parsed = summ.parse_summary_json(r.text)
        if parsed and not contains_pii(parsed['summary']):
            return dict(base, **parsed, generated=True, fallback=False, provider=r.provider), 'ok'
    ext = summ.extractive_summary(clean)
    return dict(base, **ext, generated=True, fallback=True, provider='extractive'), ('timeout' if timed_out else 'fallback')


# ------------------------------------------------------------------ KAN-58 insights
def _rate(a, b):
    return round(a / b, 3) if b else 0.0


def participation_metrics():
    reqs = MentoringRequest.objects
    total = reqs.count()
    matched = reqs.filter(status='MATCHED').count() + reqs.filter(status='CLOSED', mentorships__isnull=False).distinct().count()
    checks = AvailabilityCheck.objects.exclude(status='PENDING')
    accepted = checks.filter(status__in=['CONFIRMED', 'USED']).count()
    pairs = Mentorship.objects.select_related('request')
    # Ignore impossible negative waits (bad imported dates) so one bad row cannot skew the average
    waits = [w for w in ((p.started_at - p.request.submitted_at).total_seconds() / 86400 for p in pairs) if w >= 0]
    return {
        'approved_students': StudentProfile.objects.filter(approval_status='APPROVED').count(),
        'verified_mentors': MentorProfile.objects.filter(is_verified=True).count(),
        'open_requests': reqs.filter(status__in=['SUBMITTED', 'UNDER_REVIEW', 'WAITING']).count(),
        'total_requests': total,
        'active_mentorships': Mentorship.objects.filter(status='ACTIVE').count(),
        'meetings_held': Meeting.objects.filter(status='HELD').count(),
        'request_acceptance_rate': _rate(accepted, checks.count()),
        'request_match_rate': _rate(matched, total),
        'avg_days_request_to_match': round(sum(waits) / len(waits), 1) if waits else None,
        'popular_domains': list(reqs.values('domain').annotate(count=Count('id')).order_by('-count', 'domain')[:10]),
        'popular_pathways': list(reqs.values('pathway').annotate(count=Count('id')).order_by('-count', 'pathway')),
        'outcomes_recorded': Outcome.objects.count(),
    }


def effectiveness_metrics():
    pairs = Mentorship.objects.annotate(n=Count('meetings', filter=Q(meetings__status='HELD')))
    n_pairs = pairs.count()
    goals = Goal.objects
    active = Mentorship.objects.filter(status='ACTIVE')
    overdue = Alert.objects.filter(kind='FEEDBACK_DUE', resolved_at__isnull=True, mentorship__in=active).values('mentorship').distinct().count()
    by_path = list(Outcome.objects.values(pathway=F('mentorship__request__pathway')).annotate(count=Count('id')).order_by('pathway'))
    return {
        'meetings_per_mentorship': round(sum(p.n for p in pairs) / n_pairs, 2) if n_pairs else 0.0,
        'goals_completed_share': _rate(goals.filter(completed=True).count(), goals.count()),
        'feedback_on_time_share': _rate(active.count() - overdue, active.count()),
        'outcomes_by_pathway': by_path,
    }


# Read one mentorship's activity from the database for the risk score
def mentorship_features(pair, today=None):
    today = today or timezone.localdate()
    meetings = list(pair.meetings.values_list('session_date', 'status'))
    fb = list(pair.feedback.filter(author_id=pair.mentor_id, kind='PROGRESS').values_list('created_at', flat=True))
    goal_dates = [g for g in pair.goals.exclude(completed_at__isnull=True).values_list('completed_at', flat=True)]
    incomplete = pair.goals.filter(completed=False).count()
    alerts = pair.alerts.filter(resolved_at__isnull=True).count()
    return dropoff.extract_features(pair.started_at.date(), today, meetings, [d.date() for d in fb],
                                    [d.date() for d in goal_dates], alerts, incomplete or (0 if pair.goals.exists() else 1))


# Flags are advisory only; they never change a mentorship's status
def at_risk_mentorships(min_level='MEDIUM'):
    order = {'LOW': 0, 'MEDIUM': 1, 'HIGH': 2}
    out = []
    w = getattr(settings, 'SANGAM_RISK_WEIGHTS', None)
    for pair in Mentorship.objects.filter(status='ACTIVE').order_by('id'):
        r = dropoff.risk(mentorship_features(pair), w, getattr(settings, 'SANGAM_RISK_THRESHOLDS', None))
        if order[r['risk_level']] >= order[min_level]:
            out.append({'mentorship_id': pair.pk, 'risk_score': r['risk_score'], 'risk_level': r['risk_level'],
                        'reasons': r['reasons'], 'inactivity_rule_triggered': r['inactivity_rule_triggered'],
                        'features': r['features']})
    out.sort(key=lambda x: (-x['risk_score'], x['mentorship_id']))
    return out


# ------------------------------------------------------------------ Ask Sangam
REFUSAL = ('I cannot approve, assign or pair anyone. Only IIC staff make those decisions after a mentor confirms availability. '
           'You can track your request under My Requests or contact the IIC.')
FALLBACK_HELP = ('I can help with Sangam registration, requests, matching, meetings, goals, and feedback. '
                 'For anything requiring a verified decision or personal advice, contact the IIC.')


def retrieve_articles(message, role):
    from .models import KnowledgeArticle
    qs = list(KnowledgeArticle.objects.filter(is_published=True, audience__in=['ALL', role]).order_by('id'))
    docs = [{'title': a.title, 'content': a.content, 'obj': a} for a in qs]
    return [d['obj'] for d, _ in retrieval.top_articles(message, docs, k=3)]


# Refuse decision requests first, then answer only from published articles
OUT_OF_SCOPE = ('I can only help with questions about using Sangam: registration, mentoring requests, matching, meetings, '
                'goals, feedback and privacy. For career or study advice, request a mentor through Sangam.')
OOS_TOKEN = 'OUT_OF_SCOPE'


def chat_answer(message, role):
    """Returns (answer, sources, llm_used, scope) where scope is answered | refused_decision | out_of_scope | no_article."""
    # Guardrail 1: never approve, assign or pair anyone
    if retrieval.is_decision_request(message):
        return REFUSAL, [], False, 'refused_decision'
    # Guardrail 2: decline anything that is not about the Sangam app, before retrieval or any model call
    if retrieval.is_out_of_domain(message):
        return OUT_OF_SCOPE, [], False, 'out_of_scope'
    articles = retrieve_articles(message, role)
    if not articles:
        return FALLBACK_HELP, [], False, 'no_article'
    context = '\n'.join(f'{a.title}: {a.content[:1200]}' for a in articles)
    # Guardrail 3: the model is told to answer only Sangam questions, and to reply with a fixed token otherwise
    system = ('You are the Sangam helpdesk for the IITM BS Degree mentoring platform. Answer ONLY questions about using the Sangam app, '
              'and only from the approved knowledge below. If the question is not about Sangam, or the knowledge does not cover it, '
              f'reply with exactly {OOS_TOKEN} and nothing else. '
              'Never claim to approve mentors, students, or matches; refuse such requests and point to IIC. Do not invent policy. '
              'Do not give general career, coding or study advice. Do not ask for passwords or personal IDs. Keep answers concise.'
              '\nApproved knowledge:\n' + context)
    clean, _ = strip_pii(message[:1000])
    answer = llm.generate(clean, system=system)
    # Guardrail 4: re-check the model's reply
    if answer and OOS_TOKEN in answer:
        return OUT_OF_SCOPE, [], True, 'out_of_scope'
    used = bool(answer)
    if not answer:
        answer = 'Relevant guidance:\n' + '\n'.join(f'- {a.title}: {a.content[:220]}' for a in articles)
    return answer, [{'id': a.pk, 'title': a.title} for a in articles], used, 'answered'


def health():
    emb = get_embedder()
    emb_ok = False
    if emb is not None:
        try:
            emb.encode(['health check'])
            emb_ok = True
        except EmbeddingUnavailable:
            emb_ok = False
    return {'embedding_backend': getattr(settings, 'SANGAM_EMBEDDING_BACKEND', 'none'), 'embedding_available': emb_ok,
            'llm': llm.health(), 'fallbacks_ready': True}
