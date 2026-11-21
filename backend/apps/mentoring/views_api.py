import csv
import re
from django.db import transaction
from django.db.models import Count, Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError, PermissionDenied
from apps.accounts.permissions import iic
from apps.accounts.models import MentorProfile
from apps.assistant_ai.models import MatchSuggestionAudit
from .models import MentoringRequest, AvailabilityCheck, Mentorship, Goal, Meeting, Feedback, Outcome, Notification, AuditLog, Alert
from .serializers import RequestSerializer, AvailabilitySerializer, PairSerializer, GoalSerializer, MeetingSerializer, FeedbackSerializer, OutcomeSerializer, NotificationSerializer
from .services import send_availability, respond_availability, approve_match, close_mentorship, log, inform


def require_iic(u):
    if not iic(u): raise PermissionDenied('IIC administrator only.')

def require_student(u):
    if u.role != 'STUDENT' or not hasattr(u,'student_profile') or u.student_profile.approval_status != 'APPROVED':
        raise PermissionDenied('IIC-approved student only.')
    # Only Degree-level students can request mentoring
    if u.student_profile.level != 'DEGREE':
        raise PermissionDenied('Sangam mentoring is open to IITM BS Degree-level students only.')

def pair_for_user(pk,u,only_active=False):
    pair=get_object_or_404(Mentorship,pk=pk)
    if not iic(u) and u.pk not in (pair.student_id,pair.mentor_id):raise PermissionDenied('Not your mentorship.')
    if only_active and pair.status!='ACTIVE':raise ValidationError('Mentorship is closed.')
    return pair

def request_queryset():
    return (MentoringRequest.objects.select_related('student__student_profile', 'preferred_mentor__mentor_profile')
            .prefetch_related('availability_checks', 'mentorships'))

def pair_queryset():
    return (Mentorship.objects.select_related('student', 'mentor__mentor_profile', 'request')
            .prefetch_related('goals', 'meetings', 'outcomes', 'alerts'))

@api_view(['GET','POST'])
@permission_classes([IsAuthenticated])
def requests(request):
    if request.method=='GET':
        qs=request_queryset() if iic(request.user) else request_queryset().filter(student=request.user)
        queue = request.query_params.get('queue')
        if queue == 'review':
            qs = qs.filter(status__in=OPEN_STATUSES)
        elif queue == 'waiting':
            qs = qs.filter(status='WAITING')
        elif request.query_params.get('status'):
            qs = qs.filter(status=request.query_params['status'].upper())
        data = RequestSerializer(qs.order_by('-submitted_at')[:200], many=True, context={'request': request}).data
        return Response({'count': len(data), 'next': None, 'previous': None, 'results': data})
    require_student(request.user)
    if Mentorship.objects.filter(student=request.user,status='ACTIVE').exists():
        raise ValidationError('Student already has an active mentorship.')
    serializer=RequestSerializer(data=request.data, context={'request': request})
    serializer.is_valid(raise_exception=True)
    with transaction.atomic():
        if MentoringRequest.objects.filter(student=request.user,status__in=['SUBMITTED','UNDER_REVIEW','WAITING']).exists():
            raise ValidationError('Only one open request is allowed.')
        obj=serializer.save(student=request.user)
        log(request.user,'REQUEST_CREATED',obj)
    return Response(RequestSerializer(obj, context={'request': request}).data,status=201)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def withdraw_request(request,pk):
    require_student(request.user)
    with transaction.atomic():
        obj=get_object_or_404(MentoringRequest.objects.select_for_update(),pk=pk,student=request.user)
        if obj.status not in ('SUBMITTED','UNDER_REVIEW','WAITING'):
            raise ValidationError('Only open requests may be withdrawn.')
        obj.status='WITHDRAWN';obj.save(update_fields=['status','updated_at'])
        AvailabilityCheck.objects.filter(request=obj,status='PENDING').update(status='EXPIRED')
        log(request.user,'REQUEST_WITHDRAWN',obj)
    return Response({'id':obj.pk,'status':obj.status})

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def suggestions(request,pk):
    """Legacy route; same engine as GET /api/v1/requests/{id}/suggestions/ (KAN-46)."""
    require_iic(request.user)
    from apps.assistant_ai.views import suggestions_response
    return suggestions_response(request,pk)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def check_availability(request,pk):
    require_iic(request.user)
    try: mentor_id=int(request.data.get('mentor_id'))
    except (TypeError,ValueError):raise ValidationError({'mentor_id':'Valid mentor ID required.'})
    obj=get_object_or_404(MentoringRequest,pk=pk)
    check=send_availability(request_id=obj.pk,mentor_id=mentor_id,actor=request.user)
    return Response(AvailabilitySerializer(check).data,status=201)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def availability_inbox(request):
    if request.user.role != 'MENTOR' and not iic(request.user):raise PermissionDenied('Mentors only.')
    qs=AvailabilityCheck.objects.select_related('request', 'mentor__mentor_profile').all() if iic(request.user) else AvailabilityCheck.objects.select_related('request', 'mentor__mentor_profile').filter(mentor=request.user)
    if request.query_params.get('status'):
        qs = qs.filter(status=request.query_params['status'].upper())
    data = AvailabilitySerializer(qs.order_by('-sent_at')[:100], many=True, context={'request': request}).data
    return Response({'count': len(data), 'next': None, 'previous': None, 'results': data})

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def availability_respond(request,pk):
    if request.user.role!='MENTOR' or not hasattr(request.user,'mentor_profile') or not request.user.mentor_profile.is_verified:
        raise PermissionDenied('Verified mentor required.')
    obj=respond_availability(check_id=pk,mentor=request.user,decision=request.data.get('decision'),reason=request.data.get('reason',''))
    return Response(AvailabilitySerializer(obj).data)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def approve(request,pk):
    require_iic(request.user)
    pair=approve_match(check_id=pk,actor=request.user)
    return Response(PairSerializer(pair,context={'request':request}).data,status=201)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def mentorships(request):
    u=request.user
    qs=pair_queryset().all() if iic(u) else pair_queryset().filter(Q(student=u)|Q(mentor=u))
    if request.query_params.get('status'):
        qs = qs.filter(status=request.query_params['status'].upper())
    data = PairSerializer(qs.order_by('-started_at')[:200], many=True, context={'request': request}).data
    return Response({'count': len(data), 'next': None, 'previous': None, 'results': data})

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def close(request,pk):
    require_iic(request.user)
    reason=str(request.data.get('reason','')).strip()
    obj=close_mentorship(pair_id=pk,actor=request.user,reason=reason)
    return Response({'id':obj.pk,'status':obj.status})

@api_view(['GET','POST'])
@permission_classes([IsAuthenticated])
def goals(request,pk):
    pair=pair_for_user(pk,request.user,only_active=request.method=='POST')
    if request.method=='GET':return Response(GoalSerializer(pair.goals.order_by('slot'),many=True).data)
    if request.user.pk not in (pair.student_id,pair.mentor_id):raise PermissionDenied('Pair participant only.')
    s=GoalSerializer(data=request.data);s.is_valid(raise_exception=True)
    with transaction.atomic():
        Mentorship.objects.select_for_update().get(pk=pair.pk)
        if pair.goals.count()>=3:raise ValidationError('Maximum three shared goals.')
        if pair.goals.filter(slot=s.validated_data['slot']).exists():raise ValidationError('Goal slot already used.')
        obj=s.save(mentorship=pair,completed=False)
    return Response(GoalSerializer(obj).data,status=201)

@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def goal_complete(request,pk):
    goal=get_object_or_404(Goal,pk=pk)
    pair_for_user(goal.mentorship_id,request.user,only_active=True)
    if request.user.pk not in (goal.mentorship.student_id,goal.mentorship.mentor_id):raise PermissionDenied('Pair participant only.')
    value=request.data.get('completed')
    if not isinstance(value,bool):raise ValidationError('completed must be boolean.')
    goal.completed=value;goal.completed_at=timezone.now() if value else None;goal.save(update_fields=['completed','completed_at'])
    return Response(GoalSerializer(goal).data)

@api_view(['GET','POST'])
@permission_classes([IsAuthenticated])
def meetings(request,pk):
    pair=pair_for_user(pk,request.user,only_active=request.method=='POST')
    if request.method=='GET':return Response(MeetingSerializer(pair.meetings.all(),many=True).data)
    if request.user.pk not in (pair.student_id,pair.mentor_id):raise PermissionDenied('Pair participant only.')
    s=MeetingSerializer(data=request.data);s.is_valid(raise_exception=True)
    obj=s.save(mentorship=pair,logged_by=request.user,mentor_confirmed=(request.user.pk==pair.mentor_id))
    return Response(MeetingSerializer(obj).data,status=201)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def confirm_meeting(request,pk):
    meeting=get_object_or_404(Meeting,pk=pk)
    pair_for_user(meeting.mentorship_id,request.user,only_active=True)
    if request.user.pk!=meeting.mentorship.mentor_id:raise PermissionDenied('Mentor confirms meetings.')
    meeting.mentor_confirmed=True;meeting.save(update_fields=['mentor_confirmed'])
    return Response(MeetingSerializer(meeting).data)

@api_view(['GET','POST'])
@permission_classes([IsAuthenticated])
def feedback(request,pk):
    pair=pair_for_user(pk,request.user,only_active=False)
    if request.method=='GET':
        qs=pair.feedback.all() if iic(request.user) else pair.feedback.filter(author=request.user)
        return Response(FeedbackSerializer(qs,many=True).data)
    if request.user.pk not in (pair.student_id,pair.mentor_id):raise PermissionDenied('Pair participant only.')
    s=FeedbackSerializer(data=request.data);s.is_valid(raise_exception=True)
    obj=s.save(mentorship=pair,author=request.user)
    log(request.user,'FEEDBACK_SUBMITTED',obj,{'kind':obj.kind})
    return Response(FeedbackSerializer(obj).data,status=201)

@api_view(['GET','POST'])
@permission_classes([IsAuthenticated])
def outcomes(request,pk):
    pair=pair_for_user(pk,request.user,only_active=False)
    if request.method=='GET':return Response(OutcomeSerializer(pair.outcomes.all(),many=True).data)
    if request.user.pk!=pair.student_id:raise PermissionDenied('Student records their own outcomes.')
    s=OutcomeSerializer(data=request.data);s.is_valid(raise_exception=True)
    obj=s.save(mentorship=pair)
    return Response(OutcomeSerializer(obj).data,status=201)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def notifications(request):
    qs = request.user.sangam_notifications.all().order_by('-created_at')[:100]
    data = NotificationSerializer(qs, many=True).data
    return Response({'count': len(data), 'next': None, 'previous': None, 'results': data})

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def notification_read(request,pk):
    obj=get_object_or_404(Notification,pk=pk,recipient=request.user)
    obj.is_read=True;obj.save(update_fields=['is_read'])
    return Response({'id':pk,'is_read':True})

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def insights(request):
    """KAN-58: participation, effectiveness and at-risk count (aggregates only)."""
    require_iic(request.user)
    from apps.assistant_ai.views import insights as ai_insights
    return ai_insights(request._request)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def alerts(request):
    require_iic(request.user)
    return Response([{'id':a.pk,'mentorship_id':a.mentorship_id,'kind':a.kind,'period_start':str(a.period_start)}
                     for a in Alert.objects.filter(resolved_at__isnull=True).order_by('-created_at')[:100]])

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def audit_events(request):
    require_iic(request.user)
    qs = AuditLog.objects.select_related('actor').all().order_by('-created_at')
    data = [{'id': x.pk, 'actor_id': x.actor_id, 'actor_email': x.actor.email if x.actor else None, 'actor_role': getattr(x.actor, 'role', 'SYSTEM') if x.actor else 'SYSTEM', 'action': x.action, 'entity_type': x.entity_type, 'entity_id': x.entity_id, 'at': x.created_at.isoformat() if x.created_at else '', 'details': x.details or {}} for x in qs[:200]]
    return Response({'count': len(data), 'next': None, 'previous': None, 'results': data})

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def export_csv(request):
    require_iic(request.user)
    response=HttpResponse(content_type='text/csv')
    response['Content-Disposition']='attachment; filename="sangam_pairs.csv"'
    writer=csv.writer(response);writer.writerow(['mentorship_id','status','student_id','mentor_id','meetings','outcomes'])
    for p in Mentorship.objects.annotate(n_meetings=Count('meetings',distinct=True),n_outcomes=Count('outcomes',distinct=True)):
        writer.writerow([p.pk,p.status,p.student_id,p.mentor_id,p.n_meetings,p.n_outcomes])
    return response

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def availability_detail(request,pk):
    check=get_object_or_404(AvailabilityCheck.objects.select_related('request'),pk=pk)
    if not iic(request.user) and check.mentor_id!=request.user.pk:
        raise PermissionDenied('Not your availability check.')
    r=check.request
    def redact_personal_contact(text):
        text = re.sub(r'[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}', '[email redacted]', text or '')
        return re.sub(r'(?<!\d)(?:\+?\d[\d \-.]{8,}\d)(?!\d)', '[phone redacted]', text)
    return Response({'id':check.pk,'status':check.status,'expires_at':check.expires_at,
                     'request':{'id':r.pk,'pathway':r.pathway,'domain':r.domain,
                                'background':redact_personal_contact(r.background),
                                'problem_statement':redact_personal_contact(r.problem_statement)},
                     'student_identity_visible':False})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def request_detail(request, pk):
    obj = get_object_or_404(request_queryset(), pk=pk)
    if not iic(request.user) and obj.student_id != request.user.pk:
        raise PermissionDenied('Not your request.')
    data = RequestSerializer(obj, context={'request': request}).data
    data['timeline'] = []
    data['availability_checks'] = AvailabilitySerializer(obj.availability_checks.all(), many=True, context={'request': request}).data if iic(request.user) else None
    return Response(data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def transition(request, pk):
    require_iic(request.user)
    obj = get_object_or_404(MentoringRequest, pk=pk)
    to_status = str(request.data.get('to_status', '')).upper()
    note = str(request.data.get('note', ''))
    if to_status:
        obj.status = to_status
        obj.save(update_fields=['status', 'updated_at'])
        log(request.user, 'REQUEST_STATUS_UPDATED', obj, {'to_status': to_status, 'note': note})
    return Response(RequestSerializer(request_queryset().get(pk=pk), context={'request': request}).data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def assess(request, pk):
    require_iic(request.user)
    get_object_or_404(MentoringRequest, pk=pk)
    return Response({'suggested': 'MEDIUM', 'reason': 'Standard request assessment', 'effective': 'MEDIUM'})


@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def priority_override(request, pk):
    require_iic(request.user)
    get_object_or_404(MentoringRequest, pk=pk)
    priority = request.data.get('priority', 'MEDIUM')
    reason = request.data.get('reason', '')
    return Response({'suggested': 'MEDIUM', 'override': priority, 'override_reason': reason, 'effective': priority or 'MEDIUM'})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def mentorship_detail(request, pk):
    pair_for_user(pk, request.user)
    pair = pair_queryset().get(pk=pk)
    data = PairSerializer(pair, context={'request': request}).data
    data['timeline'] = []
    data['approved_at'] = pair.started_at
    return Response(data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def reassign(request, pk):
    require_iic(request.user)
    pair = get_object_or_404(Mentorship, pk=pk)
    reason = str(request.data.get('reason', ''))
    with transaction.atomic():
        pair.status = 'CLOSED'
        pair.closing_reason = reason
        pair.closed_at = timezone.now()
        pair.save(update_fields=['status', 'closing_reason', 'closed_at'])
        req = pair.request
        req.status = 'UNDER_REVIEW'
        req.save(update_fields=['status', 'updated_at'])
        log(request.user, 'MENTORSHIP_REASSIGNED', pair, {'reason': reason})
    return Response(RequestSerializer(request_queryset().get(pk=req.pk), context={'request': request}).data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def my_meetings(request):
    u = request.user
    qs = Meeting.objects.select_related('mentorship')
    if not iic(u):
        qs = qs.filter(Q(mentorship__student=u) | Q(mentorship__mentor=u))
    if request.query_params.get('status'):
        qs = qs.filter(status=request.query_params['status'].upper())
    data = MeetingSerializer(qs.order_by('-session_date')[:100], many=True).data
    return Response({'count': len(data), 'next': None, 'previous': None, 'results': data})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def notifications_read_all(request):
    updated = request.user.sangam_notifications.filter(is_read=False).update(is_read=True)
    return Response({'updated': updated})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def alert_resolve(request, pk):
    require_iic(request.user)
    alert = get_object_or_404(Alert, pk=pk)
    if alert.resolved_at is None:
        alert.resolved_at = timezone.now()
        alert.save(update_fields=['resolved_at'])
        log(request.user, 'ALERT_RESOLVED', alert, {'kind': alert.kind})
    return Response({'id': alert.pk, 'resolved_at': alert.resolved_at})



@api_view(['GET'])
@permission_classes([IsAuthenticated])
def calendar_status(request):
    return Response({
        'configured': False,
        'status': 'DISCONNECTED',
        'google_email': '',
        'connected_at': None
    })

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def calendar_connect(request):
    return Response({'authorization_url': ''})

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def calendar_disconnect(request):
    return Response({
        'configured': False,
        'status': 'DISCONNECTED',
        'google_email': '',
        'connected_at': None
    })

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def schedule_meeting(request, pk):
    pair = pair_for_user(pk, request.user, only_active=True)
    session_date = request.data.get('session_date') or timezone.now().date()
    duration = int(request.data.get('duration_minutes', 60))
    meeting = Meeting.objects.create(
        mentorship=pair,
        session_date=session_date,
        duration_minutes=duration,
        status='HELD',
        logged_by=request.user,
        mentor_confirmed=(request.user.pk == pair.mentor_id)
    )
    log(request.user, 'MEETING_SCHEDULED', meeting)
    return Response(MeetingSerializer(meeting).data, status=201)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def reschedule_meeting(request, pk):
    meeting = get_object_or_404(Meeting, pk=pk)
    pair_for_user(meeting.mentorship_id, request.user, only_active=True)
    if 'session_date' in request.data:
        meeting.session_date = request.data['session_date']
    if 'duration_minutes' in request.data:
        meeting.duration_minutes = int(request.data['duration_minutes'])
    meeting.save()
    log(request.user, 'MEETING_RESCHEDULED', meeting)
    return Response(MeetingSerializer(meeting).data)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def cancel_meeting(request, pk):
    meeting = get_object_or_404(Meeting, pk=pk)
    pair_for_user(meeting.mentorship_id, request.user, only_active=False)
    meeting.status = 'CANCELLED'
    meeting.save(update_fields=['status'])
    log(request.user, 'MEETING_CANCELLED', meeting)
    return Response(MeetingSerializer(meeting).data)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def record_meeting(request, pk):
    meeting = get_object_or_404(Meeting, pk=pk)
    pair_for_user(meeting.mentorship_id, request.user, only_active=False)
    new_status = request.data.get('status', 'HELD').upper()
    if new_status in ('HELD', 'NO_SHOW'):
        meeting.status = new_status
        meeting.mentor_confirmed = (request.user.pk == meeting.mentorship.mentor_id)
        meeting.save(update_fields=['status', 'mentor_confirmed'])
        log(request.user, 'MEETING_RECORDED', meeting, {'status': new_status})
    return Response(MeetingSerializer(meeting).data)
