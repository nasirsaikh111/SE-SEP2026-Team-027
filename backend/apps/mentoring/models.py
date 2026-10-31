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
    request = models.ForeignKey(MentoringRequest, on_delete=models.PROTECT, related_name='mentorships')
    availability_check = models.OneToOneField(AvailabilityCheck, on_delete=models.PROTECT, related_name='approved_mentorship')
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='student_mentorships')
    mentor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='mentor_mentorships')
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='approved_mentorships')
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.ACTIVE)
    started_at = models.DateTimeField(default=timezone.now)
    closed_at = models.DateTimeField(null=True, blank=True)
    closing_reason = models.TextField(blank=True)
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
        HELD = 'HELD', 'Held'
        CANCELLED = 'CANCELLED', 'Cancelled'
        NO_SHOW = 'NO_SHOW', 'No show'
    mentorship = models.ForeignKey(Mentorship, on_delete=models.CASCADE, related_name='meetings')
    session_date = models.DateField()
    duration_minutes = models.PositiveSmallIntegerField()
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.HELD)
    logged_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    mentor_confirmed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
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
