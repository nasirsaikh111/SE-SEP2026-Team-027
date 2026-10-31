from rest_framework.permissions import BasePermission

class IsIIC(BasePermission):
    def has_permission(self, request, view):
        u = request.user
        return bool(u and u.is_authenticated and u.is_active and (u.is_superuser or (u.role == 'ADMIN' and u.is_staff)))

class IsApprovedStudent(BasePermission):
    def has_permission(self, request, view):
        u = request.user
        return bool(u and u.is_authenticated and u.is_active and u.role == 'STUDENT' and
                    hasattr(u, 'student_profile') and u.student_profile.approval_status == 'APPROVED')

class IsVerifiedMentor(BasePermission):
    def has_permission(self, request, view):
        u = request.user
        return bool(u and u.is_authenticated and u.is_active and u.role == 'MENTOR' and
                    hasattr(u, 'mentor_profile') and u.mentor_profile.is_verified)


def iic(user):
    return bool(user.is_authenticated and (user.is_superuser or (user.role == 'ADMIN' and user.is_staff)))


def approved_student(user):
    return bool(user.is_authenticated and user.is_active and user.role == 'STUDENT' and
                hasattr(user, 'student_profile') and user.student_profile.approval_status == 'APPROVED')


class IsMentor(BasePermission):
    """Any mentor account (verified or not), e.g. for maintaining their own profile."""
    def has_permission(self, request, view):
        u = request.user
        return bool(u and u.is_authenticated and u.is_active and u.role == 'MENTOR' and hasattr(u, 'mentor_profile'))


class IsApprovedStudentOrIIC(BasePermission):
    def has_permission(self, request, view):
        return approved_student(request.user) or iic(request.user)
