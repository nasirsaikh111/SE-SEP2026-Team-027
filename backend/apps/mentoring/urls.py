from django.urls import path
from . import views_api as v
urlpatterns=[
 path('requests/',v.requests),
 path('requests/<int:pk>/withdraw/',v.withdraw_request),
 path('admin/requests/<int:pk>/suggestions/',v.suggestions),
 path('admin/requests/<int:pk>/availability/',v.check_availability),
 path('availability/',v.availability_inbox),
 path('availability/<int:pk>/respond/',v.availability_respond),
 path('admin/availability/<int:pk>/approve/',v.approve),
 path('mentorships/',v.mentorships),
 path('admin/mentorships/<int:pk>/close/',v.close),
 path('mentorships/<int:pk>/goals/',v.goals),
 path('goals/<int:pk>/complete/',v.goal_complete),
 path('mentorships/<int:pk>/meetings/',v.meetings),
 path('meetings/<int:pk>/confirm/',v.confirm_meeting),
 path('mentorships/<int:pk>/feedback/',v.feedback),
 path('mentorships/<int:pk>/outcomes/',v.outcomes),
 path('notifications/',v.notifications),
 path('notifications/<int:pk>/read/',v.notification_read),
 path('admin/insights/',v.insights),
 path('admin/alerts/',v.alerts),
 path('admin/audit/',v.audit_events),
 path('admin/export/',v.export_csv),
]
urlpatterns += [path('availability/<int:pk>/',v.availability_detail)]
