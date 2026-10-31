from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from . import views_api as v
urlpatterns=[
 path('auth/register/',v.RegisterView.as_view()),
 path('auth/token/',TokenObtainPairView.as_view()),
 path('auth/token/refresh/',TokenRefreshView.as_view()),
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
