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
