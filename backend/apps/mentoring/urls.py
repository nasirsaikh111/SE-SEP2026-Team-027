from django.urls import path
from . import views_api as v
from . import views_dashboard

urlpatterns = [
    # Dashboard
    path('dashboard/', views_dashboard.dashboard),

    # Requests
    path('requests/', v.requests),
    path('requests/<int:pk>/', v.request_detail),
    path('requests/<int:pk>/withdraw/', v.withdraw_request),
    path('requests/<int:pk>/transition/', v.transition),
    path('requests/<int:pk>/assess/', v.assess),
    path('admin/requests/<int:pk>/suggestions/', v.suggestions),
    path('admin/requests/<int:pk>/availability/', v.check_availability),

    # Availability
    path('availability/', v.availability_inbox),
    path('availability/<int:pk>/', v.availability_detail),
    path('availability/<int:pk>/respond/', v.availability_respond),
    path('admin/availability/<int:pk>/approve/', v.approve),

    # Mentorships & detail
    path('mentorships/', v.mentorships),
    path('mentorships/<int:pk>/', v.mentorship_detail),
    path('mentorships/<int:pk>/reassign/', v.reassign),
    path('admin/mentorships/<int:pk>/close/', v.close),

    # Goals
    path('mentorships/<int:pk>/goals/', v.goals),
    path('goals/<int:pk>/complete/', v.goal_complete),

    # Meetings
    path('meetings/', v.my_meetings),
    path('mentorships/<int:pk>/meetings/', v.meetings),
    path('mentorships/<int:pk>/meetings/schedule/', v.schedule_meeting),
    path('meetings/<int:pk>/confirm/', v.confirm_meeting),
    path('meetings/<int:pk>/reschedule/', v.reschedule_meeting),
    path('meetings/<int:pk>/cancel/', v.cancel_meeting),
    path('meetings/<int:pk>/record/', v.record_meeting),

    # Feedback & Outcomes
    path('mentorships/<int:pk>/feedback/', v.feedback),
    path('mentorships/<int:pk>/outcomes/', v.outcomes),

    # Notifications
    path('notifications/', v.notifications),
    path('notifications/<int:pk>/read/', v.notification_read),
    path('notifications/read-all/', v.notifications_read_all),

    # Calendar
    path('calendar/status/', v.calendar_status),
    path('calendar/connect/', v.calendar_connect),
    path('calendar/disconnect/', v.calendar_disconnect),

    # Admin insights, alerts, audit, export
    path('admin/insights/', v.insights),
    path('admin/alerts/', v.alerts),
    path('admin/alerts/<int:pk>/resolve/', v.alert_resolve),
    path('admin/audit/', v.audit_events),
    path('admin/export/', v.export_csv),
]
