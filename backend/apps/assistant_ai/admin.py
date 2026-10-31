from django.contrib import admin
from .models import KnowledgeArticle, MatchSuggestionAudit
@admin.register(KnowledgeArticle)
class KnowledgeArticleAdmin(admin.ModelAdmin):
    list_display = ('title', 'audience', 'is_published', 'updated_at')
    list_filter = ('audience', 'is_published')
    search_fields = ('title', 'content')
@admin.register(MatchSuggestionAudit)
class MatchSuggestionAuditAdmin(admin.ModelAdmin):
    list_display = ('request', 'requested_by', 'algorithm', 'candidate_count', 'used_local_llm', 'created_at')
    readonly_fields = ('request', 'requested_by', 'algorithm', 'candidate_count', 'used_local_llm', 'created_at')
    def has_add_permission(self, request): return False
    def has_change_permission(self, request, obj=None): return False
    def has_delete_permission(self, request, obj=None): return False
