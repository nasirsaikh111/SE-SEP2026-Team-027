from django.conf import settings
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.exceptions import ValidationError, PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import SimpleRateThrottle

from apps.accounts.permissions import IsIIC
from apps.mentoring.models import MentoringRequest, Mentorship, Meeting
from apps.mentoring.services import log
from .models import KnowledgeArticle, AIRequestAssessment, MeetingSummary
from . import services


class _UserThrottle(SimpleRateThrottle):
    def get_cache_key(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return None
        return self.cache_format % {'scope': self.scope, 'ident': request.user.pk}


class ChatThrottle(_UserThrottle):
    scope = 'sangam_ai_chat'


class SummaryThrottle(_UserThrottle):
    scope = 'sangam_ai_summary'


def unprocessable(field, msg):
    return Response({'detail': msg, 'field': field}, status=422)


# ------------------------------------------------------------------ Ask Sangam
@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([ChatThrottle])
def chat(request):
    question = request.data.get('message', '')
    if not isinstance(question, str) or not 2 <= len(question.strip()) <= 1000:
        raise ValidationError({'message': 'Message must be 2–1000 characters.'})
    # Deliberately NEVER save the question or answer in DB/audit logs.
    answer, sources, used_llm, scope = services.chat_answer(question, request.user.role)
    return Response({'answer': answer, 'sources': sources, 'local_ai_used': used_llm, 'llm_used': used_llm, 'scope': scope,
                     'fallback': not used_llm, 'message_stored': False, 'human_approval_required_for_matches': True})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def knowledge(request):
    qs = KnowledgeArticle.objects.filter(is_published=True, audience__in=['ALL', request.user.role]).order_by('-updated_at')[:100]
    return Response([{'id': a.pk, 'title': a.title, 'content': a.content, 'audience': a.audience} for a in qs])


# ------------------------------------------------------------------ KAN-46 suggestions
def suggestions_response(request, pk):
    raw = request.query_params.get('k', '5')
    try:
        k = int(raw)
    except (TypeError, ValueError):
        return unprocessable('k', 'k must be an integer between 1 and 20.')
    if not 1 <= k <= 20:
        return unprocessable('k', 'k must be an integer between 1 and 20.')
    obj = get_object_or_404(MentoringRequest, pk=pk)
    return Response(services.suggest_mentors(obj, request.user, k=k))


@api_view(['GET'])
@permission_classes([IsIIC])
def suggestions(request, pk):
    return suggestions_response(request, pk)


# ------------------------------------------------------------------ request priority
@api_view(['GET', 'PATCH'])
@permission_classes([IsIIC])
def request_priority(request, pk):
    obj = get_object_or_404(MentoringRequest, pk=pk)
    a = obj.ai_assessments.first()
    if request.method == 'GET':
        if a is None or request.query_params.get('refresh') in ('1', 'true'):
            a = services.assess_request_priority(obj)
        return Response(services.assessment_json(a))
    value = str(request.data.get('override_priority', '')).upper()
    reason = str(request.data.get('override_reason', '')).strip()
    if value not in AIRequestAssessment.Priority.values:
        return unprocessable('override_priority', 'override_priority must be HIGH, MEDIUM or LOW.')
    if not reason:
        return unprocessable('override_reason', 'A reason is required to override the AI priority.')
    if a is None:
        a = services.assess_request_priority(obj)
    a.override_priority, a.override_reason = value, reason[:500]
    a.overridden_by, a.overridden_at = request.user, timezone.now()
    a.save(update_fields=['override_priority', 'override_reason', 'overridden_by', 'overridden_at'])
    log(request.user, 'AI_PRIORITY_OVERRIDDEN', obj, {'assessment_id': a.pk, 'priority': value})
    return Response(services.assessment_json(a))


# ------------------------------------------------------------------ KAN-57 summaries
def _mentor_meeting(request, pk, mid):
    pair = get_object_or_404(Mentorship.objects.select_related('student', 'mentor'), pk=pk)
    if request.user.pk != pair.mentor_id or request.user.role != 'MENTOR':
        raise PermissionDenied('Only the mentor of this mentorship can use session summaries.')
    meeting = get_object_or_404(Meeting, pk=mid, mentorship=pair)
    return pair, meeting


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([SummaryThrottle])
def meeting_summary(request, pk, mid):
    pair, meeting = _mentor_meeting(request, pk, mid)
    notes = request.data.get('notes', '')
    if not isinstance(notes, str) or len(notes.strip()) < 20:
        return unprocessable('notes', 'notes must be at least 20 characters.')
    draft, status = services.summarise_notes(notes, services.known_names_for(pair))
    body = dict(draft, meeting_id=meeting.pk, stored=False, review_required=True)
    if status == 'timeout':
        return Response(dict(body, detail='LLM timed out; extractive draft returned.'), status=503)
    return Response(body)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def meeting_summary_confirm(request, pk, mid):
    pair, meeting = _mentor_meeting(request, pk, mid)
    text = request.data.get('summary', '')
    items = request.data.get('action_items', [])
    version = str(request.data.get('prompt_version', '') or 'manual')
    if not isinstance(text, str) or not text.strip():
        return unprocessable('summary', 'summary is required.')
    if not isinstance(items, list) or len(items) > 5:
        return unprocessable('action_items', 'action_items must be a list of at most 5 strings.')
    from .ml.text import strip_pii
    clean, _ = strip_pii(text[:2000], services.known_names_for(pair))
    items = [strip_pii(str(i)[:200])[0] for i in items]
    if not getattr(settings, 'SANGAM_STORE_AI_SUMMARIES', False):
        return Response({'stored': False, 'summary': clean, 'action_items': items, 'prompt_version': version,
                         'detail': 'Storage of summaries is disabled (privacy design). Copy the text you need.'})
    obj = MeetingSummary.objects.create(meeting=meeting, author=request.user, summary=clean, action_items=items,
                                        prompt_version=version[:30], generated=version != 'manual')
    log(request.user, 'AI_SUMMARY_SAVED', meeting, {'summary_id': obj.pk, 'prompt_version': obj.prompt_version})
    return Response({'stored': True, 'id': obj.pk, 'summary': obj.summary, 'action_items': obj.action_items,
                     'prompt_version': obj.prompt_version}, status=201)


# ------------------------------------------------------------------ KAN-58 insights
@api_view(['GET'])
@permission_classes([IsIIC])
def insights(request):
    from apps.mentoring.models import Alert, Outcome
    p = services.participation_metrics()
    # keep Milestone-2 keys for the existing dashboard
    legacy = {'requests': p['total_requests'], 'waiting': MentoringRequest.objects.filter(status='WAITING').count(),
              'active_pairs': p['active_mentorships'], 'meetings_held': p['meetings_held'], 'outcomes': Outcome.objects.count(),
              'alerts_open': Alert.objects.filter(resolved_at__isnull=True).count(), 'domain_demand': p['popular_domains']}
    at_risk = services.at_risk_mentorships('MEDIUM')
    return Response(dict(legacy, participation=p, effectiveness=services.effectiveness_metrics(),
                         at_risk_count=len(at_risk), aggregate_only=True))


@api_view(['GET'])
@permission_classes([IsIIC])
def insights_at_risk(request):
    level = request.query_params.get('min_level', 'MEDIUM').upper()
    if level not in ('LOW', 'MEDIUM', 'HIGH'):
        return unprocessable('min_level', 'min_level must be LOW, MEDIUM or HIGH.')
    rows = services.at_risk_mentorships(level)
    return Response({'algorithm': 'dropoff_weighted_v1', 'count': len(rows), 'results': rows,
                     'advisory_only': True, 'status_changed': False})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def health(request):
    return Response(services.health())
