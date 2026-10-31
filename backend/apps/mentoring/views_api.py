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
from apps.assistant_ai.services import ranked_candidates, explain_candidates
from .models import MentoringRequest, AvailabilityCheck, Mentorship, Goal, Meeting, Feedback, Outcome, Notification, AuditLog, Alert
from .serializers import RequestSerializer, AvailabilitySerializer, PairSerializer, GoalSerializer, MeetingSerializer, FeedbackSerializer, OutcomeSerializer, NotificationSerializer
from .services import send_availability, respond_availability, approve_match, close_mentorship, log, inform


def require_iic(u):
    if not iic(u): raise PermissionDenied('IIC administrator only.')

def require_student(u):
    if u.role != 'STUDENT' or not hasattr(u,'student_profile') or u.student_profile.approval_status != 'APPROVED':
        raise PermissionDenied('IIC-approved student only.')

def pair_for_user(pk,u,only_active=False):
    pair=get_object_or_404(Mentorship,pk=pk)
    if not iic(u) and u.pk not in (pair.student_id,pair.mentor_id):raise PermissionDenied('Not your mentorship.')
    if only_active and pair.status!='ACTIVE':raise ValidationError('Mentorship is closed.')
    return pair

@api_view(['GET','POST'])
@permission_classes([IsAuthenticated])
def requests(request):
    if request.method=='GET':
        qs=MentoringRequest.objects.all() if iic(request.user) else MentoringRequest.objects.filter(student=request.user)
        return Response(RequestSerializer(qs.order_by('-submitted_at')[:200],many=True).data)
    require_student(request.user)
    if Mentorship.objects.filter(student=request.user,status='ACTIVE').exists():
        raise ValidationError('Student already has an active mentorship.')
    serializer=RequestSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    with transaction.atomic():
        if MentoringRequest.objects.filter(student=request.user,status__in=['SUBMITTED','UNDER_REVIEW','WAITING']).exists():
            raise ValidationError('Only one open request is allowed.')
        obj=serializer.save(student=request.user)
        log(request.user,'REQUEST_CREATED',obj)
    return Response(RequestSerializer(obj).data,status=201)

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
    require_iic(request.user)
    obj=get_object_or_404(MentoringRequest,pk=pk)
    candidates=ranked_candidates(obj, limit=10)
    candidates,local_ai=explain_candidates(obj,candidates,top_n=5)
    MatchSuggestionAudit.objects.create(request=obj,requested_by=request.user,
          candidate_count=len(candidates),algorithm='rules-v1',used_local_llm=local_ai)
    return Response({'request_id':obj.pk,'candidates':candidates,'ai_explanation_used':local_ai,
        'approval_required':True,'student_cannot_choose':True})

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
    qs=AvailabilityCheck.objects.all() if iic(request.user) else AvailabilityCheck.objects.filter(mentor=request.user)
    return Response(AvailabilitySerializer(qs.order_by('-sent_at')[:100],many=True).data)

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
    qs=Mentorship.objects.all() if iic(u) else Mentorship.objects.filter(Q(student=u)|Q(mentor=u))
    return Response(PairSerializer(qs.order_by('-started_at')[:200],many=True,context={'request':request}).data)

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
    return Response(NotificationSerializer(request.user.sangam_notifications.all()[:100],many=True).data)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def notification_read(request,pk):
    obj=get_object_or_404(Notification,pk=pk,recipient=request.user)
    obj.is_read=True;obj.save(update_fields=['is_read'])
    return Response({'id':pk,'is_read':True})

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def insights(request):
    require_iic(request.user)
    return Response({'requests':MentoringRequest.objects.count(),
        'waiting':MentoringRequest.objects.filter(status='WAITING').count(),
        'active_pairs':Mentorship.objects.filter(status='ACTIVE').count(),
        'meetings_held':Meeting.objects.filter(status='HELD').count(),
        'outcomes':Outcome.objects.count(),
        'alerts_open':Alert.objects.filter(resolved_at__isnull=True).count(),
        'domain_demand':list(MentoringRequest.objects.values('domain').annotate(count=Count('id')).order_by('-count')[:20])})

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
    return Response([{'id':x.pk,'actor_id':x.actor_id,'action':x.action,'entity_type':x.entity_type,
                      'entity_id':x.entity_id,'at':x.created_at} for x in AuditLog.objects.all()[:200]])

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
