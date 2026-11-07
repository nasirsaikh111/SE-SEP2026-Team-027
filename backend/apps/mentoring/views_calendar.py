"""Google Calendar connection and meeting scheduling (mentor-driven)."""
from django.conf import settings
from django.db import transaction
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.utils import timezone
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema, inline_serializer, OpenApiParameter
from rest_framework import serializers, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError, PermissionDenied
from . import google_calendar as gcal
from .models import Meeting, GoogleCalendarConnection
from .serializers import MeetingSerializer, ScheduleMeetingSerializer, RecordMeetingSerializer
from .services import inform, log, resolve_alerts
from .views_api import pair_for_user

CalendarStatus = inline_serializer('CalendarStatus', {
    'configured': serializers.BooleanField(), 'status': serializers.ChoiceField(choices=GoogleCalendarConnection.Status.choices),
    'google_email': serializers.CharField(), 'connected_at': serializers.DateTimeField(allow_null=True)})


def require_mentor(user):
    if user.role != 'MENTOR' or not hasattr(user, 'mentor_profile'):
        raise PermissionDenied('Mentors only.')


@extend_schema(tags=['calendar'], summary='Mentor: Google Calendar connection status', responses=CalendarStatus)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def calendar_status(request):
    require_mentor(request.user)
    return Response(gcal.connection_status(request.user))


@extend_schema(tags=['calendar'], summary='Mentor: start Google OAuth; open the returned authorization_url in the browser', request=None,
               responses=inline_serializer('CalendarConnect', {'authorization_url': serializers.URLField()}))
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def calendar_connect(request):
    require_mentor(request.user)
    try:
        return Response({'authorization_url': gcal.authorization_url(request.user)})
    except gcal.CalendarNotConfigured as exc:
        return Response({'detail': str(exc), 'code': 'calendar_not_configured'}, status=status.HTTP_503_SERVICE_UNAVAILABLE)


@extend_schema(tags=['calendar'], summary='Google OAuth redirect target (browser redirect, not called by the SPA)',
               parameters=[OpenApiParameter('code', str), OpenApiParameter('state', str), OpenApiParameter('error', str)],
               request=None, responses={302: None})
@api_view(['GET'])
@permission_classes([AllowAny])
def calendar_oauth_callback(request):
    target = f'{settings.SANGAM_FRONTEND_URL}/mentor/calendar'
    if request.query_params.get('error') or not request.query_params.get('code'):
        return HttpResponseRedirect(f'{target}?calendar=denied')
    try:
        conn = gcal.complete_oauth(request.query_params['code'], request.query_params.get('state', ''))
    except gcal.CalendarError:
        return HttpResponseRedirect(f'{target}?calendar=error')
    log(conn.user, 'CALENDAR_CONNECTED', conn)
    return HttpResponseRedirect(f'{target}?calendar=connected')


@extend_schema(tags=['calendar'], summary='Mentor: disconnect Google Calendar and revoke stored tokens', request=None, responses=CalendarStatus)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def calendar_disconnect(request):
    require_mentor(request.user)
    gcal.disconnect(request.user)
    return Response(gcal.connection_status(request.user))


def _meeting_for_mentor(pk, user):
    meeting = get_object_or_404(Meeting.objects.select_related('mentorship__student', 'mentorship__mentor'), pk=pk)
    pair = pair_for_user(meeting.mentorship_id, user, only_active=True)
    if user.pk != pair.mentor_id:
        raise PermissionDenied('Only the mentor manages the meeting schedule.')
    return meeting


def _sync_response(meeting, http_status=200):
    meeting = Meeting.objects.select_related('calendar_event').get(pk=meeting.pk)
    data = MeetingSerializer(meeting).data
    event = data.get('calendar_event')
    data['calendar_synced'] = bool(event and event['sync_status'] in ('SYNCED', 'CANCELLED'))
    return Response(data, status=http_status)


def _calendar_connected(user):
    return GoogleCalendarConnection.objects.filter(user=user, status='CONNECTED').exists()


@extend_schema(tags=['calendar'], summary='Mentor: schedule a meeting; creates a Google Calendar event (and Meet link) when connected',
               request=ScheduleMeetingSerializer, responses={201: MeetingSerializer})
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def schedule_meeting(request, pk):
    pair = pair_for_user(pk, request.user, only_active=True)
    if request.user.pk != pair.mentor_id:
        raise PermissionDenied('Only the mentor schedules meetings.')
    s = ScheduleMeetingSerializer(data=request.data)
    s.is_valid(raise_exception=True)
    d = s.validated_data
    with transaction.atomic():
        meeting = Meeting.objects.create(
            mentorship=pair, session_date=d['start_at'].date(), duration_minutes=d['duration_minutes'], status='SCHEDULED',
            logged_by=request.user, start_at=d['start_at'], end_at=d['end_at'], timezone=d['timezone'],
            title=d['title'], meeting_format=d['meeting_format'])
        log(request.user, 'MEETING_SCHEDULED', meeting)
    if _calendar_connected(request.user):
        gcal.create_event(meeting, request.user, add_meet=d['add_google_meet'] and d['meeting_format'] == 'VIDEO')
    when = timezone.localtime(d['start_at'], d['start_at'].tzinfo).strftime('%d %b %Y, %H:%M')
    inform(pair.student, 'Meeting scheduled', f'Your mentor scheduled a meeting on {when} ({d["timezone"]}).')
    return _sync_response(meeting, 201)


@extend_schema(tags=['calendar'], summary='Mentor: reschedule a scheduled meeting (updates the Google event)',
               request=ScheduleMeetingSerializer, responses=MeetingSerializer)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def reschedule_meeting(request, pk):
    meeting = _meeting_for_mentor(pk, request.user)
    if meeting.status != 'SCHEDULED':
        raise ValidationError('Only scheduled meetings can be rescheduled.')
    s = ScheduleMeetingSerializer(data=request.data)
    s.is_valid(raise_exception=True)
    d = s.validated_data
    meeting.start_at, meeting.end_at, meeting.timezone = d['start_at'], d['end_at'], d['timezone']
    meeting.session_date, meeting.duration_minutes = d['start_at'].date(), d['duration_minutes']
    meeting.title = d['title'] or meeting.title
    meeting.meeting_format = d['meeting_format']
    meeting.save()
    log(request.user, 'MEETING_RESCHEDULED', meeting)
    if _calendar_connected(request.user) or hasattr(meeting, 'calendar_event'):
        gcal.update_event(meeting, request.user)
    when = timezone.localtime(d['start_at'], d['start_at'].tzinfo).strftime('%d %b %Y, %H:%M')
    inform(meeting.mentorship.student, 'Meeting rescheduled', f'Your meeting moved to {when} ({d["timezone"]}).')
    return _sync_response(meeting)


@extend_schema(tags=['calendar'], summary='Mentor: cancel a scheduled meeting (cancels the Google event)', request=None, responses=MeetingSerializer)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def cancel_meeting(request, pk):
    meeting = _meeting_for_mentor(pk, request.user)
    if meeting.status != 'SCHEDULED':
        raise ValidationError('Only scheduled meetings can be cancelled.')
    meeting.status = 'CANCELLED'
    meeting.save(update_fields=['status', 'updated_at'])
    log(request.user, 'MEETING_CANCELLED', meeting)
    gcal.cancel_event(meeting, request.user)
    inform(meeting.mentorship.student, 'Meeting cancelled', 'Your mentor cancelled an upcoming meeting.')
    return _sync_response(meeting)


@extend_schema(tags=['calendar'], summary='Participant: record whether a scheduled meeting was held (mentor record = confirmed)',
               request=RecordMeetingSerializer, responses=MeetingSerializer)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def record_meeting(request, pk):
    meeting = get_object_or_404(Meeting, pk=pk)
    pair = pair_for_user(meeting.mentorship_id, request.user, only_active=True)
    if request.user.pk not in (pair.student_id, pair.mentor_id):
        raise PermissionDenied('Pair participant only.')
    if meeting.status != 'SCHEDULED':
        raise ValidationError('Only scheduled meetings can be recorded.')
    if meeting.start_at and meeting.start_at > timezone.now():
        raise ValidationError('This meeting has not started yet.')
    s = RecordMeetingSerializer(data=request.data)
    s.is_valid(raise_exception=True)
    meeting.status = s.validated_data['status']
    meeting.duration_minutes = s.validated_data.get('duration_minutes', meeting.duration_minutes)
    meeting.mentor_confirmed = request.user.pk == pair.mentor_id
    meeting.save(update_fields=['status', 'duration_minutes', 'mentor_confirmed', 'updated_at'])
    if meeting.status == 'HELD' and meeting.mentor_confirmed:
        resolve_alerts(pair, 'INACTIVITY')
    return _sync_response(meeting)
