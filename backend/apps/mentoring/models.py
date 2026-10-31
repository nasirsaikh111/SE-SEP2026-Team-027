"""Sangam milestone-2 models: approval-gated mentorship, privacy-first logging."""
from datetime import timedelta
from django.conf import settings
from django.db import models
from django.db.models import Q
from django.utils import timezone


def seven_days_from_now():
    return timezone.now() + timedelta(days=7)

class MentoringRequest(models.Model):
    class Pathway(models.TextChoices):
        JOB = 'JOB', 'Job'
        HIGHER_STUDIES = 'HIGHER_STUDIES', 'Higher studies'
        VENTURE = 'VENTURE', 'Venture'
        UNSURE = 'UNSURE', 'Unsure'
    class Status(models.TextChoices):
        SUBMITTED = 'SUBMITTED', 'Submitted'
        UNDER_REVIEW = 'UNDER_REVIEW', 'Under review'
        WAITING = 'WAITING', 'Waiting for mentor'
        MATCHED = 'MATCHED', 'Matched'
        WITHDRAWN = 'WITHDRAWN', 'Withdrawn'
        CLOSED = 'CLOSED', 'Closed'
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='mentoring_requests')
    pathway = models.CharField(max_length=20, choices=Pathway.choices)
    domain = models.CharField(max_length=150)
    background = models.TextField(blank=True)
    problem_statement = models.TextField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.SUBMITTED, db_index=True)
    # Student preference from Discover Mentors. Advisory only: it never creates a check or a mentorship.
    preferred_mentor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='preferred_in_requests')
    submitted_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        ordering = ['submitted_at', 'id']
        constraints = [models.UniqueConstraint(fields=['student'], condition=Q(status__in=['SUBMITTED', 'UNDER_REVIEW', 'WAITING']), name='sangam_one_open_request')]
    def __str__(self):
        return f'Request {self.pk} · {self.student.email}'

class AvailabilityCheck(models.Model):
    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        CONFIRMED = 'CONFIRMED', 'Confirmed'
        DECLINED = 'DECLINED', 'Declined'
        EXPIRED = 'EXPIRED', 'Expired'
        USED = 'USED', 'Used'
    request = models.ForeignKey(MentoringRequest, on_delete=models.CASCADE, related_name='availability_checks')
    mentor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='availability_checks')
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.PENDING)
    sent_at = models.DateTimeField(default=timezone.now)
    expires_at = models.DateTimeField(default=seven_days_from_now)
    responded_at = models.DateTimeField(null=True, blank=True)
    reason = models.CharField(max_length=500, blank=True)
    class Meta:
        constraints = [models.UniqueConstraint(fields=['request'], condition=Q(status='PENDING'), name='sangam_one_pending_check')]

class Mentorship(models.Model):
    class Status(models.TextChoices):
        ACTIVE = 'ACTIVE', 'Active'
        CLOSED = 'CLOSED', 'Closed'
    class ClosureType(models.TextChoices):
        COMPLETED = 'COMPLETED', 'Completed'
        REASSIGNED = 'REASSIGNED', 'Reassigned to another mentor'
        STUDENT_WITHDREW = 'STUDENT_WITHDREW', 'Student withdrew'
        MENTOR_UNAVAILABLE = 'MENTOR_UNAVAILABLE', 'Mentor unavailable'
        OTHER = 'OTHER', 'Other'
    request = models.ForeignKey(MentoringRequest, on_delete=models.PROTECT, related_name='mentorships')
    availability_check = models.OneToOneField(AvailabilityCheck, on_delete=models.PROTECT, related_name='approved_mentorship')
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='student_mentorships')
    mentor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='mentor_mentorships')
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='approved_mentorships')
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.ACTIVE)
    started_at = models.DateTimeField(default=timezone.now)
    closed_at = models.DateTimeField(null=True, blank=True)
    closing_reason = models.TextField(blank=True)
    closure_type = models.CharField(max_length=20, choices=ClosureType.choices, blank=True)
    closed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='closed_mentorships')
    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['student'], condition=Q(status='ACTIVE'), name='sangam_one_active_student'),
            models.UniqueConstraint(fields=['mentor'], condition=Q(status='ACTIVE'), name='sangam_one_active_mentor'),
        ]

class Goal(models.Model):
    mentorship = models.ForeignKey(Mentorship, on_delete=models.CASCADE, related_name='goals')
    slot = models.PositiveSmallIntegerField()
    title = models.CharField(max_length=250)
    target_date = models.DateField()
    completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)
    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['mentorship', 'slot'], name='sangam_unique_goal_slot'),
            models.CheckConstraint(condition=Q(slot__gte=1) & Q(slot__lte=3), name='sangam_goal_slot_1_to_3'),
        ]

class Meeting(models.Model):
    class Status(models.TextChoices):
        SCHEDULED = 'SCHEDULED', 'Scheduled'
        HELD = 'HELD', 'Held'
        CANCELLED = 'CANCELLED', 'Cancelled'
        NO_SHOW = 'NO_SHOW', 'No show'
    class Format(models.TextChoices):
        VIDEO = 'VIDEO', 'Video call'
        PHONE = 'PHONE', 'Phone call'
        IN_PERSON = 'IN_PERSON', 'In person'
    mentorship = models.ForeignKey(Mentorship, on_delete=models.CASCADE, related_name='meetings')
    session_date = models.DateField()
    duration_minutes = models.PositiveSmallIntegerField()
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.HELD)
    logged_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    mentor_confirmed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    # Scheduling metadata only. Meeting records never hold discussion content.
    start_at = models.DateTimeField(null=True, blank=True)
    end_at = models.DateTimeField(null=True, blank=True)
    timezone = models.CharField(max_length=64, blank=True)
    title = models.CharField(max_length=120, blank=True)
    meeting_format = models.CharField(max_length=12, choices=Format.choices, default=Format.VIDEO)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        ordering = ['-session_date', '-id']

class Feedback(models.Model):
    class Kind(models.TextChoices):
        GENERAL = 'GENERAL', 'General'
        PROGRESS = 'PROGRESS', 'Mentor progress'
        CHANGE_MENTOR = 'CHANGE_MENTOR', 'Change mentor request'
        CLOSING = 'CLOSING', 'Closing feedback'
    mentorship = models.ForeignKey(Mentorship, on_delete=models.CASCADE, related_name='feedback')
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='feedback_authored')
    kind = models.CharField(max_length=20, choices=Kind.choices)
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        ordering = ['-created_at']

class Outcome(models.Model):
    class Kind(models.TextChoices):
        INTERVIEW = 'INTERVIEW', 'Interview cleared'
        INTERNSHIP = 'INTERNSHIP', 'Internship secured'
        JOB = 'JOB', 'Job offer'
        HIGHER_STUDIES = 'HIGHER_STUDIES', 'Admission'
        VENTURE = 'VENTURE', 'Venture milestone'
        OTHER = 'OTHER', 'Other'
    mentorship = models.ForeignKey(Mentorship, on_delete=models.CASCADE, related_name='outcomes')
    kind = models.CharField(max_length=20, choices=Kind.choices)
    achieved_on = models.DateField()
    note = models.CharField(max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

class Notification(models.Model):
    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='sangam_notifications')
    title = models.CharField(max_length=200)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        ordering = ['-created_at']

class AuditLog(models.Model):
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    action = models.CharField(max_length=80)
    entity_type = models.CharField(max_length=80)
    entity_id = models.PositiveBigIntegerField()
    details = models.JSONField(default=dict, blank=True)  # No discussion or chatbot content
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        ordering = ['-created_at']

class Alert(models.Model):
    class Kind(models.TextChoices):
        INACTIVITY = 'INACTIVITY', '14-day inactivity'
        FEEDBACK_DUE = 'FEEDBACK_DUE', 'Fortnightly mentor feedback'
    mentorship = models.ForeignKey(Mentorship, on_delete=models.CASCADE, related_name='alerts')
    kind = models.CharField(max_length=20, choices=Kind.choices)
    period_start = models.DateField()
    resolved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        constraints = [models.UniqueConstraint(fields=['mentorship', 'kind', 'period_start'], name='sangam_unique_alert_period')]


class ActivityStatusHistory(models.Model):
    """Chronological workflow transitions for request/mentorship timelines.

    Stores status codes and short system notes only: never names, contact details,
    problem statements or discussion content.
    """
    request = models.ForeignKey(MentoringRequest, on_delete=models.CASCADE, null=True, blank=True, related_name='status_history')
    mentorship = models.ForeignKey(Mentorship, on_delete=models.CASCADE, null=True, blank=True, related_name='status_history')
    event = models.CharField(max_length=40)
    from_status = models.CharField(max_length=40, blank=True)
    to_status = models.CharField(max_length=40)
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    actor_role = models.CharField(max_length=20, blank=True)
    note = models.CharField(max_length=300, blank=True)
    visible_to_student = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now, db_index=True)
    class Meta:
        ordering = ['created_at', 'id']
        verbose_name_plural = 'activity status history'


class GoogleCalendarConnection(models.Model):
    class Status(models.TextChoices):
        CONNECTED = 'CONNECTED', 'Connected'
        DISCONNECTED = 'DISCONNECTED', 'Disconnected'
        REAUTH_REQUIRED = 'REAUTH_REQUIRED', 'Reauthorization required'
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='google_calendar')
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DISCONNECTED)
    google_email = models.EmailField(blank=True)
    scopes = models.CharField(max_length=500, blank=True)
    access_token_enc = models.TextField(blank=True)   # Fernet-encrypted
    refresh_token_enc = models.TextField(blank=True)  # Fernet-encrypted
    token_expires_at = models.DateTimeField(null=True, blank=True)
    connected_at = models.DateTimeField(null=True, blank=True)
    last_error = models.CharField(max_length=300, blank=True)
    updated_at = models.DateTimeField(auto_now=True)
    def __str__(self):
        return f'{self.user.email} · {self.status}'


class MeetingCalendarEvent(models.Model):
    class SyncStatus(models.TextChoices):
        SYNCED = 'SYNCED', 'Synced'
        FAILED = 'FAILED', 'Failed'
        CANCELLED = 'CANCELLED', 'Cancelled'
    meeting = models.OneToOneField(Meeting, on_delete=models.CASCADE, related_name='calendar_event')
    provider = models.CharField(max_length=20, default='GOOGLE')
    calendar_owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    event_id = models.CharField(max_length=255, blank=True)
    html_link = models.URLField(max_length=500, blank=True)
    meet_link = models.URLField(max_length=500, blank=True)
    sync_status = models.CharField(max_length=12, choices=SyncStatus.choices, default=SyncStatus.SYNCED)
    last_synced_at = models.DateTimeField(null=True, blank=True)
    last_error = models.CharField(max_length=300, blank=True)
