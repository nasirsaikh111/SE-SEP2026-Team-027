from django.urls import path
from . import views

urlpatterns = [
    path('ai/chat/', views.chat),
    path('assistant/chat/', views.chat),
    path('ai/knowledge/', views.knowledge),
    path('admin/knowledge/', views.admin_knowledge),
    path('admin/knowledge/<int:pk>/', views.admin_knowledge_detail),
    path('ai/health/', views.health),
    path('requests/<int:pk>/suggestions/', views.suggestions),
    path('requests/<int:pk>/priority/', views.request_priority),
    path('mentorships/<int:pk>/meetings/<int:mid>/summary/', views.meeting_summary),
    path('mentorships/<int:pk>/meetings/<int:mid>/summary/confirm/', views.meeting_summary_confirm),
    path('admin/insights/at-risk/', views.insights_at_risk),
]
