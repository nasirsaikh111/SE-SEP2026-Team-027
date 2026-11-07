from django.urls import path
from rest_framework.routers import SimpleRouter
from . import views
router=SimpleRouter()
router.register('admin/knowledge',views.KnowledgeAdminViewSet,basename='admin-knowledge')
urlpatterns=[path('ai/chat/',views.chat),path('ai/knowledge/',views.knowledge)]+router.urls
