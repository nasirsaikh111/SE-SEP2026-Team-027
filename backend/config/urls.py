from django.conf import settings
from django.contrib import admin
from django.urls import include,path
from django.views.generic import TemplateView
from rest_framework.permissions import AllowAny,IsAdminUser
from drf_spectacular.views import SpectacularAPIView,SpectacularSwaggerView,SpectacularRedocView

schema_permission = [AllowAny] if settings.DEBUG else [IsAdminUser]
urlpatterns=[
    path('admin/',admin.site.urls),
    path("api-auth/", include("rest_framework.urls")),    
    path('api/v1/',include('apps.accounts.urls')),
    path('api/v1/',include('apps.mentoring.urls')),
    path('api/v1/',include('apps.assistant_ai.urls')),
    path('api/schema/',SpectacularAPIView.as_view(permission_classes=schema_permission),name='schema'),
    path('api/docs/',SpectacularSwaggerView.as_view(url_name='schema',permission_classes=schema_permission),name='swagger-ui'),
    path('api/redoc/',SpectacularRedocView.as_view(url_name='schema',permission_classes=schema_permission),name='redoc'),
    path('project-report/',TemplateView.as_view(template_name='sangam/project_report.html'),name='sangam-project-report'),
]
