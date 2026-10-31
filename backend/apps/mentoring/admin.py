from django.contrib import admin
from .models import (MentoringRequest, AvailabilityCheck, Mentorship, Goal, Meeting,
                     Feedback, Outcome, Notification, AuditLog, Alert)

@admin.register(MentoringRequest)
class MentoringRequestAdmin(admin.ModelAdmin):
    list_display = ('id', 'student', 'pathway', 'domain', 'status', 'submitted_at')
    list_filter = ('status', 'pathway', 'domain')
    search_fields = ('student__email', 'domain')
    readonly_fields = ('submitted_at', 'updated_at')

@admin.register(AvailabilityCheck)
class AvailabilityCheckAdmin(admin.ModelAdmin):
    list_display = ('id', 'request', 'mentor', 'status', 'sent_at', 'expires_at')
    list_filter = ('status',)
    readonly_fields = ('sent_at', 'responded_at')
    def has_change_permission(self, request, obj=None):
        return False
    def has_delete_permission(self, request, obj=None):
        return False
    def has_add_permission(self, request):
        return False  # Must go through availability service to enforce safeguards

@admin.register(Mentorship)
class MentorshipAdmin(admin.ModelAdmin):
    list_display = ('id', 'student', 'mentor', 'status', 'approved_by', 'started_at')
    list_filter = ('status',)
    search_fields = ('student__email', 'mentor__email')
    def has_add_permission(self, request):
        return False  # IIC must approve via checked workflow
    def has_change_permission(self, request, obj=None):
        return False  # Explicit close / reassignment workflow only
    def has_delete_permission(self, request, obj=None):
        return False

@admin.register(Goal)
class GoalAdmin(admin.ModelAdmin):
    list_display = ('id', 'mentorship', 'slot', 'title', 'target_date', 'completed')
    list_filter = ('completed',)

@admin.register(Meeting)
class MeetingAdmin(admin.ModelAdmin):
    list_display = ('id', 'mentorship', 'session_date', 'duration_minutes', 'status', 'mentor_confirmed')
    list_filter = ('status', 'mentor_confirmed')

@admin.register(Feedback)
class FeedbackAdmin(admin.ModelAdmin):
    list_display = ('id', 'mentorship', 'kind', 'author', 'created_at')
    search_fields = ('author__email',)
    readonly_fields = ('mentorship', 'author', 'kind', 'text', 'created_at')
    def has_add_permission(self, request):
        return False
    def has_delete_permission(self, request, obj=None):
        return False

@admin.register(Outcome)
class OutcomeAdmin(admin.ModelAdmin):
    list_display = ('id', 'mentorship', 'kind', 'achieved_on')
    list_filter = ('kind',)

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('recipient', 'title', 'is_read', 'created_at')
    search_fields = ('recipient__email',)

@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('id', 'actor', 'action', 'entity_type', 'entity_id', 'created_at')
    readonly_fields = ('actor', 'action', 'entity_type', 'entity_id', 'details', 'created_at')
    def has_add_permission(self, request):
        return False
    def has_change_permission(self, request, obj=None):
        return False
    def has_delete_permission(self, request, obj=None):
        return False

@admin.register(Alert)
class AlertAdmin(admin.ModelAdmin):
    list_display = ('mentorship', 'kind', 'period_start', 'resolved_at')
    list_filter = ('kind',)
