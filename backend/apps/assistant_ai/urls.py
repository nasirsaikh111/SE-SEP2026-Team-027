from django.urls import path
from . import views
urlpatterns=[path('ai/chat/',views.chat),path('ai/knowledge/',views.knowledge)]
