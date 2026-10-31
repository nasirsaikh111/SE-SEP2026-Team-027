from django.conf import settings
from django.db import models

class KnowledgeArticle(models.Model):
    class Audience(models.TextChoices):
        ALL = 'ALL', 'All logged-in users'
        STUDENT = 'STUDENT', 'Students'
        MENTOR = 'MENTOR', 'Mentors'
        ADMIN = 'ADMIN', 'IIC admins'
    title = models.CharField(max_length=180)
    content = models.TextField(help_text='Only approved non-confidential guidance; no student/mentor conversations')
    audience = models.CharField(max_length=12, choices=Audience.choices, default=Audience.ALL)
    is_published = models.BooleanField(default=False)
    updated_at = models.DateTimeField(auto_now=True)
    def __str__(self):
        return self.title

class MatchSuggestionAudit(models.Model):
    """Store only recommendation metadata, not student narrative or chatbot messages."""
    request = models.ForeignKey('mentoring.MentoringRequest', on_delete=models.CASCADE, related_name='ai_audits')
    requested_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    algorithm = models.CharField(max_length=30, default='rules-v1')
    candidate_count = models.PositiveIntegerField(default=0)
    used_local_llm = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)


class AIRequestAssessment(models.Model):
    """Advisory triage priority for the IIC queue.

    Uses only explicit deadlines in the request, waiting duration and workflow state.
    Never uses personal characteristics (CGPA, level, gender, location, etc.) and
    never changes request status or bypasses IIC approval.
    """
    class Priority(models.TextChoices):
        LOW = 'LOW', 'Low'
        MEDIUM = 'MEDIUM', 'Medium'
        HIGH = 'HIGH', 'High'
        URGENT = 'URGENT', 'Urgent'
    request = models.ForeignKey('mentoring.MentoringRequest', on_delete=models.CASCADE, related_name='ai_assessments')
    suggested_priority = models.CharField(max_length=10, choices=Priority.choices)
    explanation = models.CharField(max_length=500)
    confidence = models.DecimalField(max_digits=3, decimal_places=2, null=True, blank=True)
    factors = models.JSONField(default=dict, blank=True)  # numeric/boolean factors only, no narrative text
    algorithm = models.CharField(max_length=30, default='priority-rules-v1')
    override_priority = models.CharField(max_length=10, choices=Priority.choices, blank=True)
    override_reason = models.CharField(max_length=300, blank=True)
    overridden_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    overridden_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        ordering = ['-created_at', '-id']
    @property
    def effective_priority(self):
        return self.override_priority or self.suggested_priority
