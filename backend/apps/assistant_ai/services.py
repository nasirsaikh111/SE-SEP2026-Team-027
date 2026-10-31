"""Privacy preserving AI: deterministic candidate eligibility + optional local Ollama.
No private conversations are stored or included in matching requests.
"""
import json
import logging
import re
from urllib.request import Request, urlopen
from urllib.error import URLError
from django.conf import settings
from django.db.models import Q
from apps.accounts.models import MentorProfile
from apps.mentoring.models import Mentorship, MentoringRequest

logger = logging.getLogger(__name__)

def ollama_reply(messages):
    if not getattr(settings, 'SANGAM_OLLAMA_ENABLED', False):
        return None
    url = getattr(settings, 'SANGAM_OLLAMA_URL', 'http://127.0.0.1:11434/api/chat')
    if not url.startswith(('http://127.0.0.1:', 'http://localhost:')):
        # Do not send potentially sensitive student questions to a remote service by mistake.
        return None
    body = json.dumps({'model': getattr(settings,'SANGAM_OLLAMA_MODEL','qwen3:8b'), 'messages': messages,
                       'stream': False, 'options': {'temperature': 0.1, 'num_predict': 250}}).encode('utf8')
    try:
        req = Request(url, body, headers={'Content-Type':'application/json'}, method='POST')
        with urlopen(req, timeout=12) as response:
            result = json.load(response)
        return str(result.get('message',{}).get('content',''))[:1500]
    except (OSError, ValueError, URLError) as exc:
        logger.warning('Local Ollama unavailable: %s', type(exc).__name__)
        return None


def ranked_candidates(request_obj, limit=5):
    """Rank only eligible free alumni. AI cannot create or approve a mentorship."""
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


def explain_candidates(request_obj, candidates, top_n=5):
    """Local AI reranks *eligible* candidates with bounded semantic bonus.

    The AI never sees student/mentor names, emails, CGPA, roll IDs, or narrative;
    it cannot add candidates, bypass availability, or approve a match.
    """
    if not candidates:
        return [], False
    data = {
        'pathway': request_obj.pathway,
        'requested_domain': request_obj.domain,
        'candidates': [
            {'mentor_id': c['mentor_id'], 'domain': c['domain'],
             'specialty': c['specialty'], 'experience_years': c['experience_years']}
            for c in candidates
        ],
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
    terms = [w for w in re.findall(r'[a-zA-Z]{4,}', message.lower()) if w not in ('what','when','have','this','that')][:6]
    qs = KnowledgeArticle.objects.filter(is_published=True, audience__in=['ALL',role])
    if not terms: return list(qs.order_by('-updated_at')[:3])
    relevant = Q()
    for term in terms: relevant |= Q(title__icontains=term) | Q(content__icontains=term)
    return list(qs.filter(relevant).order_by('-updated_at')[:3])


def chat_answer(message, role):
    articles = retrieve_articles(message, role)
    if not articles:
        return ('I can help with Sangam registration, requests, matching, meetings, goals, and feedback. '
                'For anything requiring a verified decision or personal advice, contact the IIC.', [], False)
    context = '\n'.join(f'{a.title}: {a.content[:1200]}' for a in articles)
    system = ('You are Sangam helpdesk. Only answer using the supplied approved knowledge. '
              'Never claim to approve mentors, students, or matches. Do not invent policy. '
              'Do not ask for passwords or personal IDs. Keep answers concise.\nApproved knowledge:\n'+context)
    answer = ollama_reply([{'role':'system','content':system},{'role':'user','content':message[:1000]}])
    used_local_llm = bool(answer)
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
