"""Role-specific dashboard summaries. Every task carries the frontend route that performs it."""
from datetime import timedelta
from django.db.models import Count, Q
from django.utils import timezone
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from apps.accounts.models import StudentProfile, MentorProfile
from apps.accounts.permissions import iic
from . import google_calendar as gcal
from .models import MentoringRequest, AvailabilityCheck, Mentorship, Meeting, Feedback, Outcome, Alert, ActivityStatusHistory
from .serializers import RequestSerializer, PairSerializer, MeetingSerializer, AvailabilitySerializer, HistorySerializer, NotificationSerializer
from .views_api import request_queryset, pair_queryset
from .workflow import OPEN_STATUSES

FEEDBACK_INTERVAL_DAYS = 14


def task(key, label, link, count=None, tone='info'):
    return {'key': key, 'label': label, 'link': link, 'count': count, 'tone': tone}


def notifications_block(user):
    qs = user.sangam_notifications.all()
    return {'unread': qs.filter(is_read=False).count(), 'latest': NotificationSerializer(qs[:5], many=True).data}


def upcoming_meetings(pairs, limit=5):
    qs = (Meeting.objects.select_related('calendar_event').filter(mentorship__in=pairs, status='SCHEDULED', start_at__gte=timezone.now())
          .order_by('start_at')[:limit])
    return MeetingSerializer(qs, many=True).data


def student_dashboard(request, user):
    ctx = {'request': request}
    profile = getattr(user, 'student_profile', None)
    approval = profile.approval_status if profile else None
    reqs = list(request_queryset().filter(student=user).order_by('-submitted_at')[:5])
    open_req = next((r for r in reqs if r.status in OPEN_STATUSES), None)
    active = pair_queryset().filter(student=user, status='ACTIVE').first()
    goals = list(active.goals.all()) if active else []
    upcoming = upcoming_meetings([active]) if active else []
    history = (ActivityStatusHistory.objects.filter(request__student=user, visible_to_student=True).order_by('-created_at')[:6])
    tasks, steps = [], []
    if approval == 'PENDING':
        steps.append({'title': 'Registration awaiting IIC approval', 'detail': 'You can request a mentor once IIC verifies your academic details.', 'link': '/profile'})
    elif approval == 'REJECTED':
        tasks.append(task('profile_rejected', 'Update your academic profile for re-review', '/profile', tone='warning'))
    elif not open_req and not active:
        tasks.append(task('submit_request', 'Submit a mentoring request', '/discover', tone='primary'))
        steps.append({'title': 'Find a suitable mentor', 'detail': 'Browse verified mentors and describe your goal in at least 80 characters.', 'link': '/discover'})
    elif open_req:
        steps.append({'title': 'Request in progress', 'detail': 'IIC reviews every request and confirms mentor availability before pairing.', 'link': f'/requests/{open_req.pk}'})
    if active:
        if len(goals) < 3:
            tasks.append(task('add_goals', 'Agree shared goals with your mentor', '/meetings-goals', count=3 - len(goals)))
        if not upcoming:
            steps.append({'title': 'Plan your next meeting', 'detail': 'Ask your mentor to schedule the next session.', 'link': '/mentorship'})
        if not active.outcomes.exists():
            steps.append({'title': 'Record outcomes', 'detail': 'Log interviews, internships or admissions as they happen.', 'link': '/meetings-goals'})
    notes = notifications_block(user)
    if notes['unread']:
        tasks.append(task('notifications', 'Unread notifications', '/notifications', count=notes['unread']))
    return {
        'role': 'STUDENT', 'approval_status': approval,
        'rejection_reason': profile.rejection_reason if profile and approval == 'REJECTED' else '',
        'current_request': RequestSerializer(open_req, context=ctx).data if open_req else None,
        'recent_requests': RequestSerializer(reqs[:3], many=True, context=ctx).data,
        'mentorship': PairSerializer(active, context=ctx).data if active else None,
        'upcoming_meeting': upcoming[0] if upcoming else None,
        'goals': {'completed': sum(1 for g in goals if g.completed), 'total': len(goals)},
        'recent_activity': HistorySerializer(history, many=True).data,
        'notifications': notes, 'tasks': tasks, 'next_steps': steps, 'next_steps_source': 'rules-v1',
    }


def feedback_due(pair, now):
    last = Feedback.objects.filter(mentorship=pair, author=pair.mentor, kind='PROGRESS').order_by('-created_at').first()
    since = last.created_at if last else pair.started_at
    return {'due': since <= now - timedelta(days=FEEDBACK_INTERVAL_DAYS), 'last_submitted_at': last.created_at if last else None,
            'next_due_at': since + timedelta(days=FEEDBACK_INTERVAL_DAYS)}


def mentor_dashboard(request, user):
    ctx = {'request': request}
    now = timezone.now()
    profile = getattr(user, 'mentor_profile', None)
    checks = AvailabilityCheck.objects.select_related('request').filter(mentor=user, status='PENDING', expires_at__gt=now).order_by('expires_at')
    active = pair_queryset().filter(mentor=user, status='ACTIVE').first()
    upcoming = upcoming_meetings([active]) if active else []
    unconfirmed = (Meeting.objects.filter(mentorship=active, status='HELD', mentor_confirmed=False).order_by('-session_date')
                   if active else Meeting.objects.none())
    due = feedback_due(active, now) if active else None
    calendar = gcal.connection_status(user)
    tasks = []
    if checks:
        tasks.append(task('availability', 'Availability requests awaiting your response', '/mentor/availability', count=len(checks), tone='primary'))
    if unconfirmed:
        tasks.append(task('confirm_meetings', 'Meetings to confirm', '/mentor/workspace?tab=meetings', count=len(unconfirmed)))
    if due and due['due']:
        tasks.append(task('progress_feedback', 'Fortnightly progress feedback is due', '/mentor/feedback', tone='warning'))
    if active and calendar['configured'] and calendar['status'] != 'CONNECTED':
        tasks.append(task('calendar', 'Connect Google Calendar to schedule meetings', '/mentor/calendar'))
    if profile and not profile.is_verified:
        tasks.append(task('verification', 'Your profile is awaiting IIC verification', '/profile', tone='warning'))
    history = ActivityStatusHistory.objects.filter(mentorship__mentor=user).order_by('-created_at')[:6]
    return {
        'role': 'MENTOR',
        'availability': {'is_available': bool(profile and profile.is_available), 'is_verified': bool(profile and profile.is_verified),
                         'has_active_mentee': bool(active)},
        'pending_checks': AvailabilitySerializer(checks, many=True, context=ctx).data,
        'mentorship': PairSerializer(active, context=ctx).data if active else None,
        'upcoming_meetings': upcoming,
        'unconfirmed_meetings': MeetingSerializer(unconfirmed, many=True).data,
        'feedback': due, 'calendar': calendar,
        'recent_activity': HistorySerializer(history, many=True).data,
        'notifications': notifications_block(user), 'tasks': tasks,
    }


def admin_dashboard(request, user):
    ctx = {'request': request}
    now = timezone.now()
    open_reqs = request_queryset().filter(status__in=OPEN_STATUSES)
    awaiting_review = [r for r in open_reqs.order_by('submitted_at') if not any(
        c.status in ('PENDING', 'CONFIRMED') and c.expires_at > now for c in r.availability_checks.all())]
    confirmed = (AvailabilityCheck.objects.select_related('request', 'mentor__mentor_profile')
                 .filter(status='CONFIRMED', expires_at__gt=now, request__status__in=OPEN_STATUSES).order_by('expires_at'))
    counts = {
        'students_pending': StudentProfile.objects.filter(approval_status='PENDING').count(),
        'mentors_unverified': MentorProfile.objects.filter(is_verified=False).count(),
        'requests_awaiting_review': len(awaiting_review),
        'checks_pending': AvailabilityCheck.objects.filter(status='PENDING', expires_at__gt=now).count(),
        'matches_awaiting_approval': confirmed.count(),
        'active_mentorships': Mentorship.objects.filter(status='ACTIVE').count(),
        'inactivity_alerts': Alert.objects.filter(kind='INACTIVITY', resolved_at__isnull=True).count(),
        'feedback_alerts': Alert.objects.filter(kind='FEEDBACK_DUE', resolved_at__isnull=True).count(),
        'outcomes': Outcome.objects.count(),
    }
    tasks = [t for t in [
        task('students', 'Students awaiting approval', '/admin/students', counts['students_pending'], 'primary'),
        task('mentors', 'Mentors awaiting verification', '/admin/mentors?verified=false', counts['mentors_unverified']),
        task('requests', 'Requests awaiting review', '/admin/requests?queue=review', counts['requests_awaiting_review'], 'primary'),
        task('checks', 'Availability checks awaiting mentor response', '/admin/matching?tab=pending', counts['checks_pending']),
        task('approvals', 'Matches awaiting final approval', '/admin/matching?tab=confirmed', counts['matches_awaiting_approval'], 'primary'),
        task('alerts', 'Inactive mentorship alerts', '/admin/monitoring', counts['inactivity_alerts'], 'warning'),
    ] if t['count']]
    priority_rank = {'URGENT': 0, 'HIGH': 1, 'MEDIUM': 2, 'LOW': 3}
    review_rows = RequestSerializer(awaiting_review[:50], many=True, context=ctx).data
    review_rows = sorted(review_rows, key=lambda r: (priority_rank.get((r['priority'] or {}).get('effective'), 4), r['submitted_at']))[:6]
    return {
        'role': 'ADMIN', 'counts': counts, 'tasks': tasks,
        'review_queue': review_rows,
        'approval_queue': AvailabilitySerializer(confirmed[:6], many=True, context=ctx).data,
        'domain_demand': list(MentoringRequest.objects.values('domain').annotate(count=Count('id')).order_by('-count')[:8]),
        'participation': {
            'students_approved': StudentProfile.objects.filter(approval_status='APPROVED').count(),
            'students_with_requests': MentoringRequest.objects.values('student').distinct().count(),
            'mentors_verified': MentorProfile.objects.filter(is_verified=True).count(),
            'mentors_active': Mentorship.objects.filter(status='ACTIVE').values('mentor').distinct().count(),
        },
        'notifications': notifications_block(user),
    }


@extend_schema(tags=['notifications'], summary='Role-specific dashboard (landing page after login) with linked pending tasks',
               responses=OpenApiTypes.OBJECT)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dashboard(request):
    user = request.user
    if iic(user):
        data = admin_dashboard(request, user)
    elif user.role == 'MENTOR':
        data = mentor_dashboard(request, user)
    elif user.role == 'STUDENT':
        data = student_dashboard(request, user)
    else:
        data = {'role': None, 'tasks': [], 'notifications': notifications_block(user)}
    data['display_name'] = user.get_full_name() or user.email.split('@')[0]
    return Response(data)
