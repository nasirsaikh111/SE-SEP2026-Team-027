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
    """Advisory priority for a mentoring request. IIC can override; nothing is decided automatically."""
    class Priority(models.TextChoices):
        HIGH = 'HIGH', 'High'
        MEDIUM = 'MEDIUM', 'Medium'
        LOW = 'LOW', 'Low'
    request = models.ForeignKey('mentoring.MentoringRequest', on_delete=models.CASCADE, related_name='ai_assessments')
    suggested_priority = models.CharField(max_length=8, choices=Priority.choices)
    explanation = models.CharField(max_length=500)
    confidence = models.FloatField(default=0.5)
    factors = models.JSONField(default=dict, blank=True)
    algorithm = models.CharField(max_length=40)
    override_priority = models.CharField(max_length=8, choices=Priority.choices, blank=True)
    override_reason = models.CharField(max_length=500, blank=True)
    overridden_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    overridden_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at', '-id']

    @property
    def effective_priority(self):
        return self.override_priority or self.suggested_priority


class MeetingSummary(models.Model):
    """Written ONLY when the mentor confirms a draft AND settings.SANGAM_STORE_AI_SUMMARIES is on."""
    meeting = models.ForeignKey('mentoring.Meeting', on_delete=models.CASCADE, related_name='ai_summaries')
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    summary = models.TextField()
    action_items = models.JSONField(default=list, blank=True)
    prompt_version = models.CharField(max_length=30)
    generated = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
