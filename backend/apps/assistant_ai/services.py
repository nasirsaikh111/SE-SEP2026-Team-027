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
        score += min(profile.experience_years, 10)
        if profile.experience_years >= 3:
            reasons.append('Experienced alumni mentor')
        ranked.append({'mentor_id': profile.user_id, 'domain': profile.domain,
                       'specialty': profile.specialty, 'experience_years': profile.experience_years,
                       'score': score, 'reasons': reasons or ['Available verified alumnus']})
    return sorted(ranked, key=lambda item: (-item['score'],item['mentor_id']))[:limit]


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
    return sorted(candidates, key=lambda c: (-c['final_score'], c['mentor_id']))[:top_n], used_local_llm


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
