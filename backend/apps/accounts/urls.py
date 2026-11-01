from django.urls import path
from . import views_api as v
urlpatterns=[
 path('auth/register/',v.RegisterView.as_view()),
 path('auth/token/',v.SangamTokenObtainView.as_view()),
 path('auth/token/refresh/',v.SangamTokenRefreshView.as_view()),
 path('auth/me/',v.me),
 path('students/me/',v.student_profile),
 path('admin/students/',v.pending_students),
 path('admin/students/<int:pk>/review/',v.review_student),
 path('admin/mentors/',v.mentors),
 path('admin/mentors/<int:pk>/verify/',v.verify_mentor),
 path('mentor/availability/',v.mentor_availability),
]
urlpatterns += [
 path('admin/mentors/<int:pk>/invite/',v.invite_mentor),
 path('auth/mentor/activate/',v.activate_mentor),
]
urlpatterns += [
 path('admin/mentors/import/',v.import_mentors),
 path('admin/mentors/<int:pk>/',v.mentor_admin_update),
 path('mentor/profile/',v.mentor_profile),
 path('mentors/',v.MentorDirectoryView.as_view()),
 path('mentors/facets/',v.mentor_facets),
 path('mentors/<int:pk>/',v.mentor_directory_detail),
]
