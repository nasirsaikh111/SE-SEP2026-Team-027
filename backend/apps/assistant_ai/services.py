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
    qs = MentorProfile.objects.filter(user__role='MENTOR', user__is_active=True,
                                      is_verified=True, is_available=True).exclude(user_id__in=busy).select_related('user')
    desired = request_obj.domain.casefold().strip()
    words = set(re.findall(r'[a-z0-9]+', desired))
    ranked = []
    for profile in qs:
        domain = profile.domain.casefold()
        specialty = profile.specialty.casefold()
        score = 0
        reasons = []
        if desired == domain:
            score += 70; reasons.append('Exact domain alignment')
        elif desired and (desired in domain or domain in desired):
            score += 40; reasons.append('Related domain')
        if any(w in specialty for w in words if len(w)>2):
            score += 20; reasons.append('Specialty overlap')
        skills = ' '.join(str(s) for s in (profile.skills or [])).casefold()
        if any(w in skills for w in words if len(w)>2):
            score += 10; reasons.append('Relevant skills')
        if request_obj.pathway != 'UNSURE' and profile.career_path and request_obj.get_pathway_display().casefold() in profile.career_path.casefold():
            score += 10; reasons.append('Career pathway alignment')
        score += min(profile.experience_years, 10)
        if profile.experience_years >= 3:
            reasons.append('Experienced alumni mentor')
        preferred = profile.user_id == request_obj.preferred_mentor_id
        if preferred:
            reasons.append('Student preference (advisory, not scored)')
        ranked.append({'mentor_id': profile.user_id, 'name': profile.user.get_full_name() or profile.user.email,
                       'domain': profile.domain, 'specialty': profile.specialty,
                       'experience_years': profile.experience_years, 'is_student_preference': preferred,
                       'score': score, 'reasons': reasons or ['Available verified alumnus']})
    ranked.sort(key=lambda item: (-item['score'],item['mentor_id']))
    top = ranked[:limit]
    # Always surface an eligible preferred mentor to the IIC reviewer, without boosting its score.
    if request_obj.preferred_mentor_id and not any(c['is_student_preference'] for c in top):
        top += [c for c in ranked if c['is_student_preference']]
    return top


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
    messages = [
        {'role': 'system', 'content': (
            'You assist IIC human review of mentor suitability. '
            'Use only the provided anonymized structured metadata. '
            'Return STRICT JSON with one key "scores": list of objects '
            '{"mentor_id":integer,"bonus":integer 0..20,"reason":string max 120 chars}. '
            'Each listed mentor may appear at most once. Do not add unlisted mentors. '
            'Never approve/assign matches or invent achievements.')},
        {'role': 'user', 'content': json.dumps(data)},
    ]
    answer = ollama_reply(messages)
    used_local_llm = False
    if answer:
        try:
            parsed = json.loads(answer.strip().removeprefix('```json').removesuffix('```').strip())
            valid_ids = {c['mentor_id'] for c in candidates}
            scores = {}
            for row in parsed.get('scores', []):
                mid = int(row.get('mentor_id'))
                if mid not in valid_ids or mid in scores:
                    continue
                bonus = max(0, min(20, int(row.get('bonus', 0))))
                reason = re.sub(r'[\r\n\t]+', ' ', str(row.get('reason', '')))[:120]
                scores[mid] = (bonus, reason)
            if scores:
                for candidate in candidates:
                    bonus, reason = scores.get(candidate['mentor_id'], (0, ''))
                    candidate['ai_bonus'] = bonus
                    candidate['final_score'] = candidate['score'] + bonus
                    if reason:
                        candidate['reasons'].append('AI (advisory): ' + reason)
                used_local_llm = True
        except (ValueError, TypeError, AttributeError):
            logger.info('Ignoring non-JSON local AI ranking; rules-based ranking remains active')
    if not used_local_llm:
        for candidate in candidates:
            candidate['ai_bonus'] = 0
            candidate['final_score'] = candidate['score']
    ordered = sorted(candidates, key=lambda c: (-c['final_score'], c['mentor_id']))
    top = ordered[:top_n]
    top += [c for c in ordered[top_n:] if c.get('is_student_preference')]
    return top, used_local_llm


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
        answer = 'Relevant guidance:\n'+'\n'.join(f'- {a.title}: {a.content[:220]}' for a in articles)
    return answer, [{'id':a.pk, 'title':a.title} for a in articles], used_local_llm


# ---------------------------------------------------------------------------
# Advisory request priority (IIC triage). Never approves or changes status.
# ---------------------------------------------------------------------------
MONTHS = {m: i for i, m in enumerate(['jan','feb','mar','apr','may','jun','jul','aug','sep','oct','nov','dec'], start=1)}
DEADLINE_WORDS = re.compile(r'\b(deadline|due|interview|offer|closes|closing|last date|exam|submission|apply by|starts? on)\b', re.I)
ISO_DATE = re.compile(r'\b(20\d{2})-(\d{1,2})-(\d{1,2})\b')
DAY_MONTH = re.compile(r'\b(\d{1,2})(?:st|nd|rd|th)?\s+(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?(?:,?\s+(20\d{2}))?\b', re.I)
MONTH_DAY = re.compile(r'\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s+(\d{1,2})(?:st|nd|rd|th)?(?:,?\s+(20\d{2}))?\b', re.I)
RELATIVE = re.compile(r'\bin\s+(\d{1,3})\s+(day|days|week|weeks)\b', re.I)


def _days_to_deadline(text, today):
    """Smallest number of days to an explicit future date mentioned in the text (<= 365)."""
    import datetime as dt
    found = []
    def add(year, month, day, explicit_year):
        try:
            d = dt.date(int(year), int(month), int(day))
        except ValueError:
            return
        if d < today and not explicit_year:
            try:
                d = d.replace(year=d.year + 1)
            except ValueError:
                return
        if today <= d <= today + dt.timedelta(days=365):
            found.append((d - today).days)
    for y, m, d in ISO_DATE.findall(text):
        add(y, m, d, True)
    for d, mon, y in DAY_MONTH.findall(text):
        add(y or today.year, MONTHS[mon[:3].lower()], d, bool(y))
    for mon, d, y in MONTH_DAY.findall(text):
        add(y or today.year, MONTHS[mon[:3].lower()], d, bool(y))
    explicit = bool(found)
    for n, unit in RELATIVE.findall(text):
        found.append(int(n) * (7 if unit.lower().startswith('week') else 1))
    lowered = text.lower()
    if 'tomorrow' in lowered:
        found.append(1)
    if 'next week' in lowered or 'this week' in lowered:
        found.append(7)
    return (min(found) if found else None), explicit


def assess_request_priority(req):
    """Create an advisory AIRequestAssessment for an open request; returns None when not meaningful."""
    from django.utils import timezone
    from .models import AIRequestAssessment
    if req.status not in ('SUBMITTED', 'UNDER_REVIEW', 'WAITING'):
        return None
    now = timezone.now()
    text = f'{req.problem_statement}\n{req.background}'
    days, explicit = _days_to_deadline(text, timezone.localdate(now))
    keyword = bool(DEADLINE_WORDS.search(text))
    waiting_days = max(0, (now - req.submitted_at).days)
    failed_checks = req.availability_checks.filter(status__in=['DECLINED', 'EXPIRED']).count()
    score, reasons = 0, []
    if days is not None:
        if days <= 7:
            score += 50; reasons.append(f'Deadline mentioned within {days} day(s)')
        elif days <= 21:
            score += 30; reasons.append(f'Deadline mentioned in about {days} days')
        elif days <= 60:
            score += 10; reasons.append(f'Deadline mentioned in about {days} days')
    elif keyword:
        score += 10; reasons.append('Time-bound context mentioned without a specific date')
    if waiting_days >= 14:
        score += 25; reasons.append(f'Waiting {waiting_days} days')
    elif waiting_days >= 7:
        score += 15; reasons.append(f'Waiting {waiting_days} days')
    elif waiting_days >= 3:
        score += 5; reasons.append(f'Waiting {waiting_days} days')
    if failed_checks:
        score += min(20, 10 * failed_checks); reasons.append(f'{failed_checks} unsuccessful availability check(s)')
    if req.status == 'WAITING':
        score += 10; reasons.append('Waiting for an available mentor')
    priority = 'URGENT' if score >= 60 else 'HIGH' if score >= 35 else 'MEDIUM' if score >= 15 else 'LOW'
    confidence = '0.85' if explicit else '0.65' if days is not None else '0.55' if keyword else '0.50'
    explanation = '; '.join(reasons) if reasons else 'No deadline or delay signals detected'
    previous = req.ai_assessments.first()
    assessment = AIRequestAssessment.objects.create(
        request=req, suggested_priority=priority, explanation=explanation[:500], confidence=confidence,
        factors={'days_to_deadline': days, 'deadline_explicit': explicit, 'deadline_keyword': keyword,
                 'waiting_days': waiting_days, 'unsuccessful_checks': failed_checks, 'status': req.status, 'score': score},
        # An IIC override persists across re-assessments until changed.
        override_priority=previous.override_priority if previous else '',
        override_reason=previous.override_reason if previous else '',
        overridden_by=previous.overridden_by if previous else None,
        overridden_at=previous.overridden_at if previous else None)
    return assessment
