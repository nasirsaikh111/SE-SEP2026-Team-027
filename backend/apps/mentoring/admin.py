from django.contrib import admin
from .models import (MentoringRequest, AvailabilityCheck, Mentorship, Goal, Meeting,
                     Feedback, Outcome, Notification, AuditLog, Alert, ActivityStatusHistory,
                     GoogleCalendarConnection, MeetingCalendarEvent)

@admin.register(MentoringRequest)
class MentoringRequestAdmin(admin.ModelAdmin):
    list_display = ('id', 'student', 'pathway', 'domain', 'status', 'preferred_mentor', 'submitted_at')
    list_filter = ('status', 'pathway', 'domain')
    search_fields = ('student__email', 'domain')
    readonly_fields = ('submitted_at', 'updated_at', 'preferred_mentor')
    def has_change_permission(self, request, obj=None):
        return False  # Status changes go through the audited workflow services
    def has_delete_permission(self, request, obj=None):
        return False

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
    list_display = ('id', 'student', 'mentor', 'status', 'closure_type', 'approved_by', 'started_at', 'closed_at')
    list_filter = ('status', 'closure_type')
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
    list_display = ('id', 'mentorship', 'session_date', 'start_at', 'duration_minutes', 'meeting_format', 'status', 'mentor_confirmed')
    list_filter = ('status', 'mentor_confirmed', 'meeting_format')

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


@admin.register(ActivityStatusHistory)
class ActivityStatusHistoryAdmin(admin.ModelAdmin):
    list_display = ('created_at', 'request', 'mentorship', 'event', 'from_status', 'to_status', 'actor_role', 'visible_to_student')
    list_filter = ('event', 'to_status', 'actor_role')
    readonly_fields = [f.name for f in ActivityStatusHistory._meta.fields]
    def has_add_permission(self, request):
        return False
    def has_change_permission(self, request, obj=None):
        return False
    def has_delete_permission(self, request, obj=None):
        return False

@admin.register(GoogleCalendarConnection)
class GoogleCalendarConnectionAdmin(admin.ModelAdmin):
    list_display = ('user', 'status', 'google_email', 'connected_at', 'updated_at')
    list_filter = ('status',)
    search_fields = ('user__email', 'google_email')
    exclude = ('access_token_enc', 'refresh_token_enc')  # never display stored tokens
    readonly_fields = ('user', 'google_email', 'scopes', 'token_expires_at', 'connected_at', 'last_error', 'updated_at')
    def has_add_permission(self, request):
        return False

@admin.register(MeetingCalendarEvent)
class MeetingCalendarEventAdmin(admin.ModelAdmin):
    list_display = ('meeting', 'provider', 'sync_status', 'last_synced_at')
    list_filter = ('sync_status', 'provider')
    readonly_fields = [f.name for f in MeetingCalendarEvent._meta.fields]
    def has_add_permission(self, request):
        return False
