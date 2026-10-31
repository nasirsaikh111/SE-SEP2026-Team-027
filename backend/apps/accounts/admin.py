from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from .models import User, StudentProfile, MentorProfile

@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    ordering = ('email',)
    list_display = ('email', 'first_name', 'last_name', 'role', 'is_active', 'is_staff')
    list_filter = ('role', 'is_active', 'is_staff')
    search_fields = ('email', 'first_name', 'last_name')
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal', {'fields': ('first_name', 'last_name', 'role')}),
        ('Access', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Dates', {'fields': ('last_login', 'date_joined')}),
    )
    add_fieldsets = ((None, {'fields': ('email', 'password1', 'password2', 'role', 'is_active', 'is_staff')}),)

@admin.register(StudentProfile)
class StudentProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'iitm_roll_number', 'level', 'cgpa', 'approval_status', 'approved_by', 'approved_at')
    list_filter = ('approval_status', 'level')
    search_fields = ('user__email', 'iitm_roll_number')
    readonly_fields = ('approved_by', 'approved_at')
    def save_model(self, request, obj, form, change):
        from django.utils import timezone
        if change and 'approval_status' in form.changed_data:
            obj.approved_by = request.user
            obj.approved_at = timezone.now() if obj.approval_status == 'APPROVED' else None
        super().save_model(request, obj, form, change)

@admin.register(MentorProfile)
class MentorProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'domain', 'specialty', 'experience_years', 'is_verified', 'is_available')
    list_filter = ('is_verified', 'is_available', 'domain')
    search_fields = ('user__email', 'alumni_roll_number', 'domain', 'company')
