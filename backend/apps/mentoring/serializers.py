import re
from datetime import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from django.utils import timezone
from rest_framework import serializers
from apps.accounts.models import User
from apps.accounts.permissions import iic
from .models import (MentoringRequest, AvailabilityCheck, Mentorship, Goal, Meeting, Feedback, Outcome, Notification,
                     ActivityStatusHistory, MeetingCalendarEvent)
from .workflow import STAGES, STUDENT_NEXT_ACTION, IIC_NEXT_ACTION, request_stage, current_mentorship


def redact_personal_contact(text):
    text = re.sub(r'[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}', '[email redacted]', text or '')
    return re.sub(r'(?<!\d)(?:\+?\d[\d \-.]{8,}\d)(?!\d)', '[phone redacted]', text)


def viewer(serializer):
    request = serializer.context.get('request')
    return request.user if request else None


def person(user):
    return {'id': user.pk, 'name': user.get_full_name() or user.email.split('@')[0]}


class HistorySerializer(serializers.ModelSerializer):
    label = serializers.SerializerMethodField()
    class Meta:
        model = ActivityStatusHistory
        fields = ('id','event','from_status','to_status','label','actor_role','note','created_at')
    def get_label(self, obj) -> str:
        return STAGES.get(obj.to_status, obj.to_status.replace('_', ' ').title())


class RequestSerializer(serializers.ModelSerializer):
    preferred_mentor = serializers.PrimaryKeyRelatedField(queryset=User.objects.filter(role='MENTOR'), required=False, allow_null=True)
    preferred_mentor_summary = serializers.SerializerMethodField()
    stage = serializers.SerializerMethodField()
    stage_label = serializers.SerializerMethodField()
    next_action = serializers.SerializerMethodField()
    last_status_at = serializers.SerializerMethodField()
    assigned_mentor = serializers.SerializerMethodField()
    mentorship_id = serializers.SerializerMethodField()
    priority = serializers.SerializerMethodField()
    student_summary = serializers.SerializerMethodField()
    class Meta:
        model=MentoringRequest
        fields=('id','student','pathway','domain','background','problem_statement','status','submitted_at','updated_at',
                'preferred_mentor','preferred_mentor_summary','stage','stage_label','next_action','last_status_at',
                'assigned_mentor','mentorship_id','priority','student_summary')
        read_only_fields=('student','status','submitted_at','updated_at')
    def validate_problem_statement(self,value):
        if len(value.strip())<80: raise serializers.ValidationError('Minimum 80 characters required.')
        return value
    def validate_preferred_mentor(self, mentor):
        if mentor is None:
            return None
        profile = getattr(mentor, 'mentor_profile', None)
        if not (mentor.is_active and profile and profile.is_verified and profile.is_discoverable):
            raise serializers.ValidationError('Choose a mentor from the Discover Mentors directory.')
        return mentor
    def _stage(self, obj):
        if not hasattr(obj, '_sangam_stage'):
            obj._sangam_stage = request_stage(obj)
        return obj._sangam_stage
    def get_stage(self, obj) -> str:
        return self._stage(obj)
    def get_stage_label(self, obj) -> str:
        return STAGES.get(self._stage(obj), obj.get_status_display())
    def get_next_action(self, obj) -> str:
        table = IIC_NEXT_ACTION if iic(viewer(self)) else STUDENT_NEXT_ACTION
        return table.get(self._stage(obj), '')
    def get_last_status_at(self, obj) -> datetime:
        history = list(obj.status_history.all())
        return history[-1].created_at if history else obj.updated_at
    def get_preferred_mentor_summary(self, obj) -> dict | None:
        m = obj.preferred_mentor
        if not m:
            return None
        profile = getattr(m, 'mentor_profile', None)
        return {**person(m), 'current_role': profile.current_role if profile else '', 'company': profile.company if profile else ''}
    def _approved_pair(self, obj):
        return current_mentorship(obj) if obj.status in ('MATCHED', 'CLOSED') else None
    def get_assigned_mentor(self, obj) -> dict | None:
        # Only after IIC final approval (a Mentorship exists).
        pair = self._approved_pair(obj)
        return person(pair.mentor) if pair else None
    def get_mentorship_id(self, obj) -> int | None:
        pair = self._approved_pair(obj)
        return pair.pk if pair else None
    def get_priority(self, obj) -> dict | None:
        if not iic(viewer(self)):
            return None
        assessments = list(obj.ai_assessments.all())
        if not assessments or obj.status not in ('SUBMITTED', 'UNDER_REVIEW', 'WAITING'):
            return None
        a = assessments[0]
        return {'assessment_id': a.pk, 'effective': a.effective_priority, 'suggested': a.suggested_priority,
                'explanation': a.explanation, 'confidence': float(a.confidence) if a.confidence is not None else None,
                'overridden': bool(a.override_priority), 'override_reason': a.override_reason, 'assessed_at': a.created_at}
    def get_student_summary(self, obj) -> dict | None:
        if not iic(viewer(self)):
            return None
        s = obj.student
        profile = getattr(s, 'student_profile', None)
        return {**person(s), 'email': s.email, 'approval_status': profile.approval_status if profile else None,
                'level': profile.level if profile else None}


class RequestDetailSerializer(RequestSerializer):
    timeline = serializers.SerializerMethodField()
    availability_checks = serializers.SerializerMethodField()
    class Meta(RequestSerializer.Meta):
        fields = RequestSerializer.Meta.fields + ('timeline','availability_checks')
    def get_timeline(self, obj) -> list:
        rows = obj.status_history.all()
        if not iic(viewer(self)):
            rows = [r for r in rows if r.visible_to_student]
        return HistorySerializer(rows, many=True).data
    def get_availability_checks(self, obj) -> list | None:
        if not iic(viewer(self)):
            return None
        return AvailabilitySerializer(obj.availability_checks.order_by('-sent_at'), many=True, context=self.context).data


class AvailabilitySerializer(serializers.ModelSerializer):
    request_summary = serializers.SerializerMethodField()
    mentor_summary = serializers.SerializerMethodField()
    is_expired = serializers.SerializerMethodField()
    class Meta:
        model=AvailabilityCheck
        fields=('id','request','mentor','status','sent_at','expires_at','responded_at','reason',
                'request_summary','mentor_summary','is_expired')
        read_only_fields=fields
    def get_request_summary(self, obj) -> dict:
        # Anonymised: no student identity or contact details before IIC approval.
        r = obj.request
        return {'id': r.pk, 'pathway': r.pathway, 'domain': r.domain,
                'problem_statement': redact_personal_contact(r.problem_statement)}
    def get_mentor_summary(self, obj) -> dict | None:
        if not iic(viewer(self)):
            return None
        profile = getattr(obj.mentor, 'mentor_profile', None)
        return {**person(obj.mentor), 'domain': profile.domain if profile else '',
                'is_student_preference': obj.request.preferred_mentor_id == obj.mentor_id}
    def get_is_expired(self, obj) -> bool:
        return obj.status == 'EXPIRED' or (obj.status in ('PENDING', 'CONFIRMED') and obj.expires_at <= timezone.now())


class PairSerializer(serializers.ModelSerializer):
    student_contact=serializers.SerializerMethodField()
    mentor_contact=serializers.SerializerMethodField()
    student_name=serializers.SerializerMethodField()
    mentor_name=serializers.SerializerMethodField()
    mentor_profile=serializers.SerializerMethodField()
    request_summary=serializers.SerializerMethodField()
    progress=serializers.SerializerMethodField()
    open_alerts=serializers.SerializerMethodField()
    class Meta:
        model=Mentorship
        fields=('id','request','student','mentor','status','started_at','closed_at','student_contact','mentor_contact',
                'student_name','mentor_name','mentor_profile','request_summary','closure_type','closing_reason',
                'progress','open_alerts')
    def _can_see(self, obj):
        u=viewer(self)
        return bool(u and (iic(u) or u.pk in (obj.student_id,obj.mentor_id)))
    def get_student_contact(self,obj) -> str | None:
        return obj.student.email if self._can_see(obj) else None
    def get_mentor_contact(self,obj) -> str | None:
        return obj.mentor.email if self._can_see(obj) else None
    def get_student_name(self, obj) -> str | None:
        return person(obj.student)['name'] if self._can_see(obj) else None
    def get_mentor_name(self, obj) -> str | None:
        return person(obj.mentor)['name'] if self._can_see(obj) else None
    def get_mentor_profile(self, obj) -> dict | None:
        profile = getattr(obj.mentor, 'mentor_profile', None)
        if not profile or not self._can_see(obj):
            return None
        return {'current_role': profile.current_role, 'company': profile.company, 'domain': profile.domain,
                'specialty': profile.specialty, 'linkedin_url': profile.linkedin_url}
    def get_request_summary(self, obj) -> dict:
        return {'id': obj.request_id, 'domain': obj.request.domain, 'pathway': obj.request.pathway, 'status': obj.request.status}
    def get_progress(self, obj) -> dict:
        goals = list(obj.goals.all())
        meetings = list(obj.meetings.all())
        held = [m for m in meetings if m.status == 'HELD']
        now = timezone.now()
        upcoming = sorted((m for m in meetings if m.status == 'SCHEDULED' and m.start_at and m.start_at >= now), key=lambda m: m.start_at)
        return {'goals_total': len(goals), 'goals_completed': sum(1 for g in goals if g.completed),
                'meetings_held': len(held), 'meetings_total': len(meetings),
                'last_meeting_date': max((m.session_date for m in held), default=None),
                'next_meeting': MeetingSerializer(upcoming[0], context=self.context).data if upcoming else None,
                'outcomes': len(obj.outcomes.all())}
    def get_open_alerts(self, obj) -> list | None:
        if not iic(viewer(self)):
            return None
        return [a.kind for a in obj.alerts.all() if a.resolved_at is None]


class GoalSerializer(serializers.ModelSerializer):
    class Meta:
        model=Goal
        fields=('id','mentorship','slot','title','target_date','completed','completed_at')
        read_only_fields=('mentorship','completed_at')


class CalendarEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = MeetingCalendarEvent
        fields = ('provider','html_link','meet_link','sync_status','last_synced_at','last_error')


class MeetingSerializer(serializers.ModelSerializer):
    calendar_event = serializers.SerializerMethodField()
    class Meta:
        model=Meeting
        fields=('id','mentorship','session_date','duration_minutes','status','logged_by','mentor_confirmed','created_at',
                'start_at','end_at','timezone','title','meeting_format','calendar_event')
        read_only_fields=('mentorship','logged_by','mentor_confirmed','created_at','start_at','end_at','timezone','title')
    def validate_duration_minutes(self,v):
        if v<1 or v>720:raise serializers.ValidationError('Duration must be 1–720 minutes.')
        return v
    def validate_status(self, v):
        if v == 'SCHEDULED':
            raise serializers.ValidationError('Use the schedule endpoint to create upcoming meetings.')
        return v
    def validate(self, data):
        if data.get('status', 'HELD') in ('HELD', 'NO_SHOW') and data.get('session_date') and data['session_date'] > timezone.localdate():
            raise serializers.ValidationError({'session_date': 'A held meeting cannot be in the future.'})
        return data
    def get_calendar_event(self, obj) -> dict | None:
        event = getattr(obj, 'calendar_event', None) if hasattr(obj, 'calendar_event') else None
        return CalendarEventSerializer(event).data if event else None


class ScheduleMeetingSerializer(serializers.Serializer):
    date = serializers.DateField()
    start_time = serializers.TimeField()
    end_time = serializers.TimeField()
    timezone = serializers.CharField(max_length=64, default='Asia/Kolkata')
    title = serializers.CharField(max_length=120, required=False, allow_blank=True, default='')
    meeting_format = serializers.ChoiceField(choices=Meeting.Format.choices, default=Meeting.Format.VIDEO)
    add_google_meet = serializers.BooleanField(default=True)
    def validate(self, data):
        try:
            tz = ZoneInfo(data['timezone'])
        except (ZoneInfoNotFoundError, ValueError):
            raise serializers.ValidationError({'timezone': 'Unknown time zone.'})
        start = datetime.combine(data['date'], data['start_time'], tzinfo=tz)
        end = datetime.combine(data['date'], data['end_time'], tzinfo=tz)
        if end <= start:
            raise serializers.ValidationError({'end_time': 'End time must be after the start time.'})
        minutes = int((end - start).total_seconds() // 60)
        if minutes > 720:
            raise serializers.ValidationError({'end_time': 'Meetings are limited to 12 hours.'})
        if start <= timezone.now():
            raise serializers.ValidationError({'start_time': 'Choose a future start time.'})
        data.update(start_at=start, end_at=end, duration_minutes=minutes)
        return data


class RecordMeetingSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=[('HELD', 'Held'), ('NO_SHOW', 'No show')])
    duration_minutes = serializers.IntegerField(min_value=1, max_value=720, required=False)


class FeedbackSerializer(serializers.ModelSerializer):
    class Meta:
        model=Feedback
        fields=('id','mentorship','author','kind','text','created_at')
        read_only_fields=('mentorship','author','created_at')
    def validate_text(self,v):
        if not v.strip():raise serializers.ValidationError('Written feedback is required.')
        if len(v) > 4000:raise serializers.ValidationError('Feedback is limited to 4000 characters.')
        return v

class OutcomeSerializer(serializers.ModelSerializer):
    class Meta:
        model=Outcome
        fields=('id','mentorship','kind','achieved_on','note','created_at')
        read_only_fields=('mentorship','created_at')

class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model=Notification
        fields=('id','title','message','is_read','created_at')
        read_only_fields=('id','title','message','created_at')
