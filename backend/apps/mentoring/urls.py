from django.urls import path
from . import views_api as v
from . import views_calendar as cal
from . import views_dashboard as dash
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
urlpatterns += [
 path('dashboard/',dash.dashboard),
 path('requests/<int:pk>/',v.request_detail),
 path('admin/requests/<int:pk>/transition/',v.transition),
 path('admin/requests/<int:pk>/assess/',v.assess),
 path('admin/requests/<int:pk>/priority/',v.priority_override),
 path('mentorships/<int:pk>/',v.mentorship_detail),
 path('admin/mentorships/<int:pk>/reassign/',v.reassign),
 path('meetings/',v.my_meetings),
 path('mentorships/<int:pk>/meetings/schedule/',cal.schedule_meeting),
 path('meetings/<int:pk>/reschedule/',cal.reschedule_meeting),
 path('meetings/<int:pk>/cancel/',cal.cancel_meeting),
 path('meetings/<int:pk>/record/',cal.record_meeting),
 path('notifications/read-all/',v.notifications_read_all),
 path('admin/alerts/<int:pk>/resolve/',v.alert_resolve),
 path('calendar/status/',cal.calendar_status),
 path('calendar/connect/',cal.calendar_connect),
 path('calendar/oauth/callback/',cal.calendar_oauth_callback),
 path('calendar/disconnect/',cal.calendar_disconnect),
]
urlpatterns += [
 path('admin/daily-checks/',v.daily_checks),
 path('cron/daily/',v.cron_daily_checks),
]
