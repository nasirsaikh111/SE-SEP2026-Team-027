import csv
import hmac
from datetime import datetime, time, timedelta
from django.conf import settings
from django.db import transaction
from django.db.models import Count, Q, Prefetch
from django.db.models.functions import TruncMonth
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema, inline_serializer, OpenApiParameter
from rest_framework import serializers
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError, PermissionDenied
from apps.accounts.models import StudentProfile, MentorProfile
from apps.accounts.pagination import list_response
from apps.accounts.permissions import iic, approved_student
from apps.assistant_ai.models import MatchSuggestionAudit, AIRequestAssessment
from apps.assistant_ai.services import ranked_candidates, explain_candidates, assess_request_priority
from .models import (MentoringRequest, AvailabilityCheck, Mentorship, Goal, Meeting, Feedback, Outcome, Notification,
                     AuditLog, Alert, ActivityStatusHistory)
from .serializers import (RequestSerializer, RequestDetailSerializer, AvailabilitySerializer, PairSerializer, GoalSerializer,
                          MeetingSerializer, FeedbackSerializer, OutcomeSerializer, NotificationSerializer, HistorySerializer,
                          redact_personal_contact)
from .services import (send_availability, respond_availability, approve_match, close_mentorship, reassign_mentorship,
                       transition_request, create_request, withdraw_request as withdraw_service, log, inform_iic, resolve_alerts,
                       expire_overdue_checks, run_daily_checks)
from .workflow import OPEN_STATUSES, request_stage


def doc(tag, summary, **kwargs):
    kwargs.setdefault('request', None)
    kwargs.setdefault('responses', OpenApiTypes.OBJECT)
    return extend_schema(tags=[tag], summary=summary, **kwargs)


def require_iic(u):
    if not iic(u): raise PermissionDenied('IIC administrator only.')

def require_student(u):
    if not approved_student(u):
        raise PermissionDenied('IIC-approved student only.')

def pair_for_user(pk,u,only_active=False):
    pair=get_object_or_404(Mentorship,pk=pk)
    if not iic(u) and u.pk not in (pair.student_id,pair.mentor_id):raise PermissionDenied('Not your mentorship.')
    if only_active and pair.status!='ACTIVE':raise ValidationError('Mentorship is closed.')
    return pair


def request_queryset():
    return (MentoringRequest.objects.select_related('student__student_profile', 'preferred_mentor__mentor_profile')
            .prefetch_related('availability_checks', Prefetch('mentorships', queryset=Mentorship.objects.select_related('mentor')),
                              'status_history', Prefetch('ai_assessments', queryset=AIRequestAssessment.objects.order_by('-created_at', '-id'))))


def pair_queryset():
    return (Mentorship.objects.select_related('student', 'mentor__mentor_profile', 'request')
            .prefetch_related('goals', Prefetch('meetings', queryset=Meeting.objects.select_related('calendar_event')), 'outcomes', 'alerts'))


@doc('requests', 'List mentoring requests (own for students, all for IIC) or submit one (approved students)',
     request=RequestSerializer, responses=RequestSerializer(many=True),
     parameters=[OpenApiParameter('status', str, description='Comma-separated persisted statuses (IIC)'),
                 OpenApiParameter('stage', str, description='Derived stage, e.g. AWAITING_IIC_APPROVAL (IIC)'),
                 OpenApiParameter('search', str, description='Domain or student name/email (IIC)'),
                 OpenApiParameter('page', int, description='Opt-in pagination')])
@api_view(['GET','POST'])
@permission_classes([IsAuthenticated])
def requests(request):
    if request.method=='GET':
        qs=request_queryset()
        if iic(request.user):
            if request.query_params.get('status'):
                qs=qs.filter(status__in=[s.strip().upper() for s in request.query_params['status'].split(',')])
            term=request.query_params.get('search','').strip()
            if term:
                qs=qs.filter(Q(domain__icontains=term)|Q(student__email__icontains=term)|Q(student__first_name__icontains=term)|Q(student__last_name__icontains=term))
        else:
            qs=qs.filter(student=request.user)
        qs=qs.order_by('-submitted_at')
        stage=request.query_params.get('stage','').strip().upper()
        if stage and iic(request.user):
            qs=[r for r in qs.filter(status__in=OPEN_STATUSES+('MATCHED',))[:500] if request_stage(r)==stage]
        return list_response(request, qs, lambda rows: RequestSerializer(rows,many=True,context={'request':request}).data)
    require_student(request.user)
    serializer=RequestSerializer(data=request.data,context={'request':request})
    serializer.is_valid(raise_exception=True)
    obj=create_request(student=request.user,data=serializer.validated_data)
    return Response(RequestSerializer(request_queryset().get(pk=obj.pk),context={'request':request}).data,status=201)


@doc('requests', 'Request details with chronological status timeline', responses=RequestDetailSerializer)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def request_detail(request, pk):
    obj=get_object_or_404(request_queryset(),pk=pk)
    if not iic(request.user) and obj.student_id!=request.user.pk:
        raise PermissionDenied('Not your request.')
    return Response(RequestDetailSerializer(obj,context={'request':request}).data)


@doc('requests', 'Student: withdraw an open request',
     responses=inline_serializer('WithdrawResult', {'id': serializers.IntegerField(), 'status': serializers.CharField()}))
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def withdraw_request(request,pk):
    require_student(request.user)
    obj=withdraw_service(request_id=pk,student=request.user)
    return Response({'id':obj.pk,'status':obj.status})


@doc('requests', 'IIC: start review, mark waiting, or close an open request',
     request=inline_serializer('RequestTransition', {'to_status': serializers.ChoiceField(choices=['UNDER_REVIEW','WAITING','CLOSED']),
                                                     'note': serializers.CharField(required=False)}),
     responses=RequestSerializer)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def transition(request, pk):
    require_iic(request.user)
    get_object_or_404(MentoringRequest,pk=pk)
    transition_request(request_id=pk,actor=request.user,to_status=str(request.data.get('to_status','')).upper(),note=str(request.data.get('note','')))
    return Response(RequestSerializer(request_queryset().get(pk=pk),context={'request':request}).data)


@doc('requests', 'IIC: re-run the advisory AI priority assessment for an open request')
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def assess(request, pk):
    require_iic(request.user)
    obj=get_object_or_404(MentoringRequest,pk=pk)
    if not assess_request_priority(obj):
        raise ValidationError('Priority is only assessed for open requests.')
    return Response(RequestSerializer(request_queryset().get(pk=pk),context={'request':request}).data['priority'])


@doc('requests', 'IIC: override (or clear) the suggested priority. Never changes request status.',
     request=inline_serializer('PriorityOverride', {'priority': serializers.ChoiceField(choices=['', 'LOW','MEDIUM','HIGH','URGENT']),
                                                    'reason': serializers.CharField(required=False)}))
@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def priority_override(request, pk):
    require_iic(request.user)
    obj=get_object_or_404(MentoringRequest,pk=pk)
    value=str(request.data.get('priority','')).upper()
    reason=str(request.data.get('reason','')).strip()
    if value and value not in AIRequestAssessment.Priority.values:
        raise ValidationError({'priority':'Use LOW, MEDIUM, HIGH, URGENT or an empty string to clear.'})
    if value and not reason:
        raise ValidationError({'reason':'A reason is required for an override.'})
    a=obj.ai_assessments.first() or assess_request_priority(obj)
    if not a:
        raise ValidationError('Priority is only available for open requests.')
    a.override_priority=value;a.override_reason=reason[:300] if value else ''
    a.overridden_by=request.user if value else None;a.overridden_at=timezone.now() if value else None
    a.save(update_fields=['override_priority','override_reason','overridden_by','overridden_at'])
    log(request.user,'PRIORITY_OVERRIDE',obj,{'priority':value or None})
    return Response(RequestSerializer(request_queryset().get(pk=pk),context={'request':request}).data['priority'])


@doc('availability', 'IIC: advisory mentor suggestions (AI recommends, IIC decides)')
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def suggestions(request,pk):
    require_iic(request.user)
    obj=get_object_or_404(MentoringRequest,pk=pk)
    candidates=ranked_candidates(obj, limit=10)
    candidates,local_ai=explain_candidates(obj,candidates,top_n=5)
    MatchSuggestionAudit.objects.create(request=obj,requested_by=request.user,
          candidate_count=len(candidates),algorithm='rules-v1',used_local_llm=local_ai)
    return Response({'request_id':obj.pk,'candidates':candidates,'ai_explanation_used':local_ai,
        'approval_required':True,'student_cannot_choose':True,'student_preference_mentor_id':obj.preferred_mentor_id})

@doc('availability', 'IIC: send a 7-day availability check to a mentor',
     request=inline_serializer('SendAvailability', {'mentor_id': serializers.IntegerField()}), responses=AvailabilitySerializer)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def check_availability(request,pk):
    require_iic(request.user)
    try: mentor_id=int(request.data.get('mentor_id'))
    except (TypeError,ValueError):raise ValidationError({'mentor_id':'Valid mentor ID required.'})
    obj=get_object_or_404(MentoringRequest,pk=pk)
    check=send_availability(request_id=obj.pk,mentor_id=mentor_id,actor=request.user)
    return Response(AvailabilitySerializer(check,context={'request':request}).data,status=201)

@doc('availability', 'Availability checks: own for mentors, all for IIC',
     responses=AvailabilitySerializer(many=True), parameters=[OpenApiParameter('status', str, description='PENDING, CONFIRMED, DECLINED, EXPIRED, USED')])
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def availability_inbox(request):
    if request.user.role != 'MENTOR' and not iic(request.user):raise PermissionDenied('Mentors only.')
    expire_overdue_checks()  # 7-day rule holds between daily cron runs
    qs=AvailabilityCheck.objects.select_related('request','mentor__mentor_profile')
    qs=qs if iic(request.user) else qs.filter(mentor=request.user)
    if request.query_params.get('status'):
        qs=qs.filter(status__in=[s.strip().upper() for s in request.query_params['status'].split(',')])
    return list_response(request, qs.order_by('-sent_at'),
                         lambda rows: AvailabilitySerializer(rows,many=True,context={'request':request}).data, legacy_limit=100)

@doc('availability', 'Mentor: confirm or decline an availability check',
     request=inline_serializer('AvailabilityResponse', {'decision': serializers.ChoiceField(choices=['CONFIRMED','DECLINED']),
                                                        'reason': serializers.CharField(required=False)}),
     responses=AvailabilitySerializer)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def availability_respond(request,pk):
    if request.user.role!='MENTOR' or not hasattr(request.user,'mentor_profile') or not request.user.mentor_profile.is_verified:
        raise PermissionDenied('Verified mentor required.')
    get_object_or_404(AvailabilityCheck,pk=pk)
    obj=respond_availability(check_id=pk,mentor=request.user,decision=request.data.get('decision'),reason=request.data.get('reason',''))
    return Response(AvailabilitySerializer(obj,context={'request':request}).data)

@doc('mentorships', 'IIC: final approval of a mentor-confirmed pairing (creates the active mentorship)', responses=PairSerializer)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def approve(request,pk):
    require_iic(request.user)
    get_object_or_404(AvailabilityCheck,pk=pk)
    pair=approve_match(check_id=pk,actor=request.user)
    return Response(PairSerializer(pair_queryset().get(pk=pair.pk),context={'request':request}).data,status=201)

@doc('mentorships', 'Mentorships: own for participants, all for IIC', responses=PairSerializer(many=True),
     parameters=[OpenApiParameter('status', str, description='ACTIVE or CLOSED')])
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def mentorships(request):
    u=request.user
    qs=pair_queryset() if iic(u) else pair_queryset().filter(Q(student=u)|Q(mentor=u))
    if request.query_params.get('status'):
        qs=qs.filter(status=request.query_params['status'].upper())
    return list_response(request, qs.order_by('-started_at'), lambda rows: PairSerializer(rows,many=True,context={'request':request}).data)


def mentorship_timeline(pair, user):
    """Milestones only: workflow transitions, meeting metadata, goal completions and outcomes."""
    history=ActivityStatusHistory.objects.filter(Q(mentorship=pair)|Q(request=pair.request))
    if not iic(user):
        history=history.filter(mentorship=pair) if user.pk==pair.mentor_id else history.filter(visible_to_student=True)
    items=[{'type':'status','at':h.created_at,'title':HistorySerializer(h).data['label'],'detail':h.note,'event':h.event} for h in history]
    for m in pair.meetings.all():
        when=m.start_at or timezone.make_aware(datetime.combine(m.session_date,time.min))
        items.append({'type':'meeting','at':when,'title':f'Meeting {m.get_status_display().lower()}',
                      'detail':f'{m.duration_minutes} min · {m.get_meeting_format_display()}','event':m.status})
    for g in pair.goals.all():
        if g.completed and g.completed_at:
            items.append({'type':'goal','at':g.completed_at,'title':'Goal completed','detail':g.title,'event':'GOAL_COMPLETED'})
    for o in pair.outcomes.all():
        items.append({'type':'outcome','at':o.created_at,'title':o.get_kind_display(),'detail':o.note,'event':'OUTCOME'})
    return sorted(items,key=lambda i:i['at'],reverse=True)


@doc('mentorships', 'Mentorship details with milestone timeline (participants and IIC)')
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def mentorship_detail(request, pk):
    pair_for_user(pk,request.user)
    pair=pair_queryset().get(pk=pk)
    data=PairSerializer(pair,context={'request':request}).data
    data['timeline']=mentorship_timeline(pair,request.user)
    data['approved_at']=pair.started_at
    return Response(data)

@doc('mentorships', 'IIC: close an active mentorship with a reason',
     request=inline_serializer('CloseMentorship', {'reason': serializers.CharField(),
                                                   'closure_type': serializers.ChoiceField(choices=Mentorship.ClosureType.choices, required=False)}))
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def close(request,pk):
    require_iic(request.user)
    get_object_or_404(Mentorship,pk=pk)
    reason=str(request.data.get('reason','')).strip()
    closure_type=str(request.data.get('closure_type','COMPLETED')).upper()
    if closure_type=='REASSIGNED':
        raise ValidationError({'closure_type':'Use the reassign endpoint to reassign a mentor.'})
    obj=close_mentorship(pair_id=pk,actor=request.user,reason=reason,closure_type=closure_type)
    return Response({'id':obj.pk,'status':obj.status,'closure_type':obj.closure_type})


@doc('mentorships', 'IIC: close the pairing and reopen the request for a new mentor',
     request=inline_serializer('ReassignMentorship', {'reason': serializers.CharField()}), responses=RequestSerializer)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def reassign(request, pk):
    require_iic(request.user)
    get_object_or_404(Mentorship,pk=pk)
    req=reassign_mentorship(pair_id=pk,actor=request.user,reason=str(request.data.get('reason','')))
    return Response(RequestSerializer(request_queryset().get(pk=req.pk),context={'request':request}).data)

@doc('workspace', 'Shared goals (maximum three per mentorship)', request=GoalSerializer, responses=GoalSerializer(many=True))
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

@doc('workspace', 'Mark a shared goal complete or incomplete',
     request=inline_serializer('GoalComplete', {'completed': serializers.BooleanField()}), responses=GoalSerializer)
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

@doc('workspace', 'Meeting records for a mentorship (GET) or log a past meeting (POST). Metadata only.',
     request=MeetingSerializer, responses=MeetingSerializer(many=True))
@api_view(['GET','POST'])
@permission_classes([IsAuthenticated])
def meetings(request,pk):
    pair=pair_for_user(pk,request.user,only_active=request.method=='POST')
    if request.method=='GET':return Response(MeetingSerializer(pair.meetings.select_related('calendar_event'),many=True).data)
    if request.user.pk not in (pair.student_id,pair.mentor_id):raise PermissionDenied('Pair participant only.')
    s=MeetingSerializer(data=request.data);s.is_valid(raise_exception=True)
    obj=s.save(mentorship=pair,logged_by=request.user,mentor_confirmed=(request.user.pk==pair.mentor_id))
    if obj.status=='HELD' and obj.mentor_confirmed:
        resolve_alerts(pair,'INACTIVITY')
    return Response(MeetingSerializer(obj).data,status=201)

@doc('workspace', 'Mentor: confirm a meeting logged by the student', responses=MeetingSerializer)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def confirm_meeting(request,pk):
    meeting=get_object_or_404(Meeting,pk=pk)
    pair_for_user(meeting.mentorship_id,request.user,only_active=True)
    if request.user.pk!=meeting.mentorship.mentor_id:raise PermissionDenied('Mentor confirms meetings.')
    meeting.mentor_confirmed=True;meeting.save(update_fields=['mentor_confirmed'])
    if meeting.status=='HELD':
        resolve_alerts(meeting.mentorship,'INACTIVITY')
    return Response(MeetingSerializer(meeting).data)


@doc('workspace', 'My meetings across mentorships (participants; IIC sees all)', responses=MeetingSerializer(many=True),
     parameters=[OpenApiParameter('upcoming', bool), OpenApiParameter('status', str)])
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def my_meetings(request):
    u=request.user
    qs=Meeting.objects.select_related('calendar_event','mentorship')
    if not iic(u):
        qs=qs.filter(Q(mentorship__student=u)|Q(mentorship__mentor=u))
    if request.query_params.get('upcoming')=='true':
        qs=qs.filter(status='SCHEDULED',start_at__gte=timezone.now()).order_by('start_at')
    if request.query_params.get('status'):
        qs=qs.filter(status=request.query_params['status'].upper())
    return list_response(request, qs, lambda rows: MeetingSerializer(rows,many=True).data)


FEEDBACK_AUTHORS={'PROGRESS':'MENTOR','CHANGE_MENTOR':'STUDENT'}

@doc('workspace', 'Written feedback to IIC (no ratings). Visible only to its author and IIC staff.',
     request=FeedbackSerializer, responses=FeedbackSerializer(many=True))
@api_view(['GET','POST'])
@permission_classes([IsAuthenticated])
def feedback(request,pk):
    pair=pair_for_user(pk,request.user,only_active=False)
    if request.method=='GET':
        qs=pair.feedback.all() if iic(request.user) else pair.feedback.filter(author=request.user)
        return Response(FeedbackSerializer(qs,many=True).data)
    if request.user.pk not in (pair.student_id,pair.mentor_id):raise PermissionDenied('Pair participant only.')
    s=FeedbackSerializer(data=request.data);s.is_valid(raise_exception=True)
    kind=s.validated_data['kind']
    author_role='MENTOR' if request.user.pk==pair.mentor_id else 'STUDENT'
    if FEEDBACK_AUTHORS.get(kind,author_role)!=author_role:
        raise ValidationError({'kind':f'{kind} feedback is submitted by the {FEEDBACK_AUTHORS[kind].lower()}.'})
    if pair.status!='ACTIVE' and kind!='CLOSING':
        raise ValidationError({'kind':'Only closing feedback can be sent after a mentorship ends.'})
    if kind=='CLOSING' and pair.feedback.filter(author=request.user,kind='CLOSING').exists():
        raise ValidationError({'kind':'You have already sent closing feedback for this mentorship.'})
    obj=s.save(mentorship=pair,author=request.user)
    log(request.user,'FEEDBACK_SUBMITTED',obj,{'kind':obj.kind})
    if kind=='PROGRESS':
        resolve_alerts(pair,'FEEDBACK_DUE')
    if kind in ('CHANGE_MENTOR','CLOSING'):
        inform_iic('Mentorship feedback needs review',f'{obj.get_kind_display()} submitted for mentorship #{pair.pk}.')
    return Response(FeedbackSerializer(obj).data,status=201)

@doc('workspace', 'Career outcomes (recorded by the student)', request=OutcomeSerializer, responses=OutcomeSerializer(many=True))
@api_view(['GET','POST'])
@permission_classes([IsAuthenticated])
def outcomes(request,pk):
    pair=pair_for_user(pk,request.user,only_active=False)
    if request.method=='GET':return Response(OutcomeSerializer(pair.outcomes.all(),many=True).data)
    if request.user.pk!=pair.student_id:raise PermissionDenied('Student records their own outcomes.')
    s=OutcomeSerializer(data=request.data);s.is_valid(raise_exception=True)
    obj=s.save(mentorship=pair)
    log(request.user,'OUTCOME_RECORDED',obj,{'kind':obj.kind})
    return Response(OutcomeSerializer(obj).data,status=201)

@doc('notifications', 'My notifications (newest first)', responses=NotificationSerializer(many=True),
     parameters=[OpenApiParameter('unread', bool)])
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def notifications(request):
    qs=request.user.sangam_notifications.all()
    if request.query_params.get('unread')=='true':
        qs=qs.filter(is_read=False)
    return list_response(request, qs, lambda rows: NotificationSerializer(rows,many=True).data, legacy_limit=100)

@doc('notifications', 'Mark one notification as read')
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def notification_read(request,pk):
    obj=get_object_or_404(Notification,pk=pk,recipient=request.user)
    obj.is_read=True;obj.save(update_fields=['is_read'])
    return Response({'id':pk,'is_read':True})


@doc('notifications', 'Mark all my notifications as read')
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def notifications_read_all(request):
    updated=request.user.sangam_notifications.filter(is_read=False).update(is_read=True)
    return Response({'updated':updated})


def monthly_series(qs, field, months=6):
    """Counts per calendar month for the last `months` months, ending with the current month."""
    today=timezone.localdate()
    index=today.year*12+today.month-1-(months-1)
    start=today.replace(year=index//12,month=index%12+1,day=1)
    rows=qs.filter(**{f'{field}__date__gte':start}).annotate(m=TruncMonth(field)).values('m').annotate(n=Count('id'))
    counts={r['m'].strftime('%Y-%m'):r['n'] for r in rows if r['m']}
    out,cursor=[],start
    for _ in range(months):
        key=cursor.strftime('%Y-%m');out.append({'month':key,'count':counts.get(key,0)})
        cursor=(cursor+timedelta(days=32)).replace(day=1)
    return out


@doc('reports', 'IIC: programme insights for dashboards and analytics')
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def insights(request):
    require_iic(request.user)
    now=timezone.now()
    return Response({'requests':MentoringRequest.objects.count(),
        'waiting':MentoringRequest.objects.filter(status='WAITING').count(),
        'active_pairs':Mentorship.objects.filter(status='ACTIVE').count(),
        'meetings_held':Meeting.objects.filter(status='HELD').count(),
        'outcomes':Outcome.objects.count(),
        'alerts_open':Alert.objects.filter(resolved_at__isnull=True).count(),
        'domain_demand':list(MentoringRequest.objects.values('domain').annotate(count=Count('id')).order_by('-count')[:20]),
        'students_pending':StudentProfile.objects.filter(approval_status='PENDING').count(),
        'mentors_unverified':MentorProfile.objects.filter(is_verified=False).count(),
        'mentors_verified':MentorProfile.objects.filter(is_verified=True).count(),
        'checks_pending':AvailabilityCheck.objects.filter(status='PENDING',expires_at__gt=now).count(),
        'matches_awaiting_approval':AvailabilityCheck.objects.filter(status='CONFIRMED',expires_at__gt=now,request__status__in=OPEN_STATUSES).count(),
        'mentorships_closed':Mentorship.objects.filter(status='CLOSED').count(),
        'requests_by_status':list(MentoringRequest.objects.values('status').annotate(count=Count('id')).order_by('status')),
        'pathway_demand':list(MentoringRequest.objects.values('pathway').annotate(count=Count('id')).order_by('-count')),
        'outcomes_by_kind':list(Outcome.objects.values('kind').annotate(count=Count('id')).order_by('-count')),
        'closure_types':list(Mentorship.objects.filter(status='CLOSED').values('closure_type').annotate(count=Count('id'))),
        'monthly_requests':monthly_series(MentoringRequest.objects.all(),'submitted_at'),
        'monthly_mentorships':monthly_series(Mentorship.objects.all(),'started_at'),
        'monthly_meetings':monthly_series(Meeting.objects.filter(status='HELD'),'created_at')})

@doc('reports', 'IIC: monitoring alerts (14-day inactivity, fortnightly feedback due)',
     parameters=[OpenApiParameter('include_resolved', bool)])
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def alerts(request):
    require_iic(request.user)
    qs=Alert.objects.select_related('mentorship__student','mentorship__mentor').order_by('-created_at')
    if request.query_params.get('include_resolved')!='true':
        qs=qs.filter(resolved_at__isnull=True)
    return Response([{'id':a.pk,'mentorship_id':a.mentorship_id,'kind':a.kind,'period_start':str(a.period_start),
                      'kind_label':a.get_kind_display(),'created_at':a.created_at,'resolved_at':a.resolved_at,
                      'student_name':a.mentorship.student.get_full_name() or a.mentorship.student.email,
                      'mentor_name':a.mentorship.mentor.get_full_name() or a.mentorship.mentor.email} for a in qs[:100]])


@doc('reports', 'IIC: resolve a monitoring alert')
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def alert_resolve(request, pk):
    require_iic(request.user)
    alert=get_object_or_404(Alert,pk=pk)
    if alert.resolved_at is None:
        alert.resolved_at=timezone.now();alert.save(update_fields=['resolved_at'])
        log(request.user,'ALERT_RESOLVED',alert,{'kind':alert.kind})
    return Response({'id':alert.pk,'resolved_at':alert.resolved_at})

DAILY_SUMMARY=inline_serializer('DailyChecksResult', {'expired_checks': serializers.IntegerField(), 'inactivity_alerts': serializers.IntegerField(),
                                                     'feedback_alerts': serializers.IntegerField(), 'priorities_refreshed': serializers.IntegerField()})

@doc('reports', 'IIC: run the daily monitoring checks now (7-day expiry, 14-day inactivity, fortnightly feedback)', responses=DAILY_SUMMARY)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def daily_checks(request):
    require_iic(request.user)
    summary=run_daily_checks()
    log(request.user,'DAILY_CHECKS_RUN',request.user,summary)
    return Response(summary)


@doc('reports', 'Scheduler: daily monitoring checks. Requires "Authorization: Bearer <CRON_SECRET>" (sent by Vercel Cron).', responses=DAILY_SUMMARY)
@api_view(['GET','POST'])
@authentication_classes([])
@permission_classes([AllowAny])
def cron_daily_checks(request):
    secret=getattr(settings,'CRON_SECRET','')
    supplied=request.headers.get('Authorization','')
    if not secret or not hmac.compare_digest(supplied.encode(),f'Bearer {secret}'.encode()):
        raise PermissionDenied('Invalid scheduler credentials.')
    return Response(run_daily_checks())


@doc('reports', 'IIC: chronological audit trail of approvals and status changes',
     parameters=[OpenApiParameter('action', str), OpenApiParameter('entity_type', str), OpenApiParameter('page', int)])
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def audit_events(request):
    require_iic(request.user)
    qs=AuditLog.objects.select_related('actor')
    for key in ('action','entity_type'):
        if request.query_params.get(key):
            qs=qs.filter(**{key:request.query_params[key]})
    serialize=lambda rows: [{'id':x.pk,'actor_id':x.actor_id,'action':x.action,'entity_type':x.entity_type,
                             'entity_id':x.entity_id,'at':x.created_at,'actor_email':x.actor.email if x.actor else None,
                             'actor_role':('ADMIN' if iic(x.actor) else x.actor.role) if x.actor else 'SYSTEM','details':x.details} for x in rows]
    return list_response(request, qs, serialize)


EXPORTS={
    'pairs':(['mentorship_id','status','student_id','mentor_id','meetings','outcomes'],
             lambda: ([p.pk,p.status,p.student_id,p.mentor_id,p.n_meetings,p.n_outcomes] for p in
                      Mentorship.objects.annotate(n_meetings=Count('meetings',distinct=True),n_outcomes=Count('outcomes',distinct=True)))),
    'requests':(['request_id','status','pathway','domain','student_id','preferred_mentor_id','submitted_at'],
                lambda: ([r.pk,r.status,r.pathway,r.domain,r.student_id,r.preferred_mentor_id or '',r.submitted_at.isoformat()]
                         for r in MentoringRequest.objects.order_by('pk'))),
    'outcomes':(['outcome_id','mentorship_id','kind','achieved_on'],
                lambda: ([o.pk,o.mentorship_id,o.kind,o.achieved_on.isoformat()] for o in Outcome.objects.order_by('pk'))),
    'meetings':(['meeting_id','mentorship_id','session_date','duration_minutes','status','mentor_confirmed'],
                lambda: ([m.pk,m.mentorship_id,m.session_date.isoformat(),m.duration_minutes,m.status,m.mentor_confirmed]
                         for m in Meeting.objects.order_by('pk'))),
}

@doc('reports', 'IIC: CSV export (IDs and metadata only; no narrative or contact data)', responses={(200, 'text/csv'): OpenApiTypes.STR},
     parameters=[OpenApiParameter('type', str, description='pairs (default), requests, outcomes or meetings')])
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def export_csv(request):
    require_iic(request.user)
    kind=request.query_params.get('type','pairs')
    if kind not in EXPORTS: raise ValidationError({'type':f'Use one of: {", ".join(EXPORTS)}.'})
    header,rows=EXPORTS[kind]
    response=HttpResponse(content_type='text/csv')
    response['Content-Disposition']=f'attachment; filename="sangam_{kind}.csv"'
    writer=csv.writer(response);writer.writerow(header)
    for row in rows():
        writer.writerow(row)
    log(request.user,'CSV_EXPORT',request.user,{'type':kind})
    return response

@doc('availability', 'Availability check details for the addressed mentor (student identity hidden)')
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def availability_detail(request,pk):
    check=get_object_or_404(AvailabilityCheck.objects.select_related('request'),pk=pk)
    if not iic(request.user) and check.mentor_id!=request.user.pk:
        raise PermissionDenied('Not your availability check.')
    r=check.request
    return Response({'id':check.pk,'status':check.status,'expires_at':check.expires_at,
                     'request':{'id':r.pk,'pathway':r.pathway,'domain':r.domain,
                                'background':redact_personal_contact(r.background),
                                'problem_statement':redact_personal_contact(r.problem_statement)},
                     'student_identity_visible':False})
