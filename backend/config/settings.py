"""
Django settings for the Sangam backend.

All secrets and environment-specific values are read from environment variables
(optionally loaded from ``backend/.env``). See ``backend/.env.example``.
"""

import os
import sys
from datetime import timedelta
from pathlib import Path

import dj_database_url
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / '.env')  # never overrides variables already set in the environment


def env_bool(name, default=False):
    return os.getenv(name, str(default)).strip().lower() in ('1', 'true', 'yes', 'on')


def env_list(name, default=''):
    return [item.strip() for item in os.getenv(name, default).split(',') if item.strip()]


#DEBUG = env_bool('DJANGO_DEBUG', False)
DEBUG = True
SECRET_KEY = os.getenv('DJANGO_SECRET_KEY', '')
if not SECRET_KEY:
    if not DEBUG and 'test' not in sys.argv:
        raise RuntimeError('DJANGO_SECRET_KEY must be set when DJANGO_DEBUG is false.')
    SECRET_KEY = 'django-insecure-local-development-only'

ALLOWED_HOSTS = env_list('DJANGO_ALLOWED_HOSTS', 'localhost,127.0.0.1')

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'rest_framework_simplejwt',
    'django_filters',
    'drf_spectacular',
    'corsheaders',
    'apps.accounts',
    'apps.mentoring',
    'apps.assistant_ai',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'
ASGI_APPLICATION = 'config.asgi.application'
AUTH_USER_MODEL = 'accounts.User'

# Database: DATABASE_URL (e.g. the Supabase pooler URL) or local SQLite.
# The test runner always uses an in-memory SQLite database unless
# SANGAM_TEST_USE_DATABASE_URL=true, so tests never touch the shared database.
# Alternatively set POSTGRES_HOST/POSTGRES_PORT/POSTGRES_DB/POSTGRES_USER/POSTGRES_PASSWORD,
# which avoids URL-encoding the password.
DATABASE_URL = os.getenv('DATABASE_URL', '').strip()
RUNNING_TESTS = len(sys.argv) > 1 and sys.argv[1] == 'test'
USE_CONFIGURED_DB = not (RUNNING_TESTS and not env_bool('SANGAM_TEST_USE_DATABASE_URL'))
if USE_CONFIGURED_DB and os.getenv('POSTGRES_HOST'):
    DATABASES = {'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'HOST': os.getenv('POSTGRES_HOST'),
        'PORT': os.getenv('POSTGRES_PORT', '5432'),
        'NAME': os.getenv('POSTGRES_DB', 'postgres'),
        'USER': os.getenv('POSTGRES_USER', 'postgres'),
        'PASSWORD': os.getenv('POSTGRES_PASSWORD', ''),
        'CONN_MAX_AGE': 60,
        'OPTIONS': {'sslmode': 'require' if env_bool('DATABASE_SSL_REQUIRE', True) else 'prefer', 'connect_timeout': 15},
    }}
elif USE_CONFIGURED_DB and DATABASE_URL:
    is_postgres = DATABASE_URL.startswith(('postgres://', 'postgresql://'))
    try:
        DATABASES = {'default': dj_database_url.parse(DATABASE_URL, conn_max_age=60, ssl_require=is_postgres and env_bool('DATABASE_SSL_REQUIRE', True))}
    except ValueError:
        raise RuntimeError('DATABASE_URL is not a valid URL. Remove any [square brackets] around the password and '
                           'percent-encode special characters (e.g. @ as %40), or use the POSTGRES_* variables instead.') from None
    if is_postgres:
        DATABASES['default'].setdefault('OPTIONS', {})['connect_timeout'] = 15
else:
    DATABASES = {'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': BASE_DIR / 'db.sqlite3'}}

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Kolkata'
USE_I18N = True
USE_TZ = True
STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

EMAIL_BACKEND = os.getenv('DJANGO_EMAIL_BACKEND', 'django.core.mail.backends.console.EmailBackend')
EMAIL_HOST = os.getenv('EMAIL_HOST', 'localhost')
EMAIL_PORT = int(os.getenv('EMAIL_PORT', '587'))
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD', '')
EMAIL_USE_TLS = env_bool('EMAIL_USE_TLS', True)
DEFAULT_FROM_EMAIL = os.getenv('DEFAULT_FROM_EMAIL', 'Sangam IIC <no-reply@sangam.local>')

SANGAM_FRONTEND_URL = os.getenv('SANGAM_FRONTEND_URL', 'https://sangam-step2.vercel.app').rstrip('/')
CORS_ALLOWED_ORIGINS = env_list('CORS_ALLOWED_ORIGINS', f'{SANGAM_FRONTEND_URL},http://localhost:5173,http://127.0.0.1:5173')
CSRF_TRUSTED_ORIGINS = env_list('CSRF_TRUSTED_ORIGINS', SANGAM_FRONTEND_URL)

if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_CONTENT_TYPE_NOSNIFF = True

REST_FRAMEWORK = {
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
        'rest_framework.renderers.BrowsableAPIRenderer',
    ],
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_FILTER_BACKENDS': ['django_filters.rest_framework.DjangoFilterBackend'],
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    'EXCEPTION_HANDLER': 'apps.accounts.exceptions.sangam_exception_handler',
    'DEFAULT_THROTTLE_RATES': {
        'sangam_ai_chat': '10/minute',
        'sangam_auth': '20/minute',
    },
    'DEFAULT_PAGINATION_CLASS': 'apps.accounts.pagination.SangamPagination',
    'PAGE_SIZE': 50,
}

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=int(os.getenv('JWT_ACCESS_MINUTES', '30'))),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=int(os.getenv('JWT_REFRESH_DAYS', '1'))),
    'UPDATE_LAST_LOGIN': True,
}

SPECTACULAR_SETTINGS = {
    'TITLE': 'Sangam API',
    'DESCRIPTION': ('IIC-approved student mentoring API. No ratings or conversation logging. '
                    'AI features are advisory only: they never approve students, mentors or matches.'),
    'VERSION': '1.1.0',
    'SERVE_INCLUDE_SCHEMA': False,
    'COMPONENT_SPLIT_REQUEST': True,
    'SCHEMA_PATH_PREFIX': r'/api/v1',
    'ENUM_NAME_OVERRIDES': {
        'RequestStatusEnum': 'apps.mentoring.models.MentoringRequest.Status',
        'AvailabilityStatusEnum': 'apps.mentoring.models.AvailabilityCheck.Status',
        'MentorshipStatusEnum': 'apps.mentoring.models.Mentorship.Status',
        'MeetingStatusEnum': 'apps.mentoring.models.Meeting.Status',
        'CalendarStatusEnum': 'apps.mentoring.models.GoogleCalendarConnection.Status',
        'ApprovalStatusEnum': 'apps.accounts.models.StudentProfile.ApprovalStatus',
    },
    'TAGS': [
        {'name': 'auth', 'description': 'Authentication, registration and the current user'},
        {'name': 'students', 'description': 'Student profile and IIC registration approval'},
        {'name': 'mentors', 'description': 'Mentor repository, discovery and mentor self-service'},
        {'name': 'requests', 'description': 'Mentoring requests, status history and AI priority'},
        {'name': 'availability', 'description': 'IIC availability checks and mentor confirmation'},
        {'name': 'mentorships', 'description': 'IIC match approval, active mentorships, closure and reassignment'},
        {'name': 'workspace', 'description': 'Goals, meetings, written feedback and outcomes'},
        {'name': 'calendar', 'description': 'Google Calendar connection and meeting scheduling'},
        {'name': 'notifications', 'description': 'Notifications and dashboards'},
        {'name': 'reports', 'description': 'IIC insights, alerts, audit log and CSV exports'},
        {'name': 'ai', 'description': 'Helpdesk chatbot and knowledge management'},
    ],
}

# Ollama runs on the SAME computer hosting Django. No student data is sent to cloud AI.
SANGAM_OLLAMA_ENABLED = env_bool('SANGAM_OLLAMA_ENABLED', True)
SANGAM_OLLAMA_URL = os.getenv('SANGAM_OLLAMA_URL', 'http://127.0.0.1:11434/api/chat')
SANGAM_OLLAMA_MODEL = os.getenv('SANGAM_OLLAMA_MODEL', 'qwen3:8b')

# Google Calendar (OAuth 2.0 web flow). Leave blank to disable the integration.
GOOGLE_OAUTH_CLIENT_ID = os.getenv('GOOGLE_OAUTH_CLIENT_ID', '')
GOOGLE_OAUTH_CLIENT_SECRET = os.getenv('GOOGLE_OAUTH_CLIENT_SECRET', '')
GOOGLE_OAUTH_REDIRECT_URI = os.getenv('GOOGLE_OAUTH_REDIRECT_URI', 'http://127.0.0.1:8000/api/v1/calendar/oauth/callback/')
# Fernet key used to encrypt stored Google tokens; derived from SECRET_KEY when unset.
SANGAM_TOKEN_ENCRYPTION_KEY = os.getenv('SANGAM_TOKEN_ENCRYPTION_KEY', '')

SANGAM_DOCS_DIR = BASE_DIR.parent / 'docs'

if RUNNING_TESTS:
    PASSWORD_HASHERS = ['django.contrib.auth.hashers.MD5PasswordHasher']  # speed only; never used outside tests
    SANGAM_OLLAMA_ENABLED = env_bool('SANGAM_TEST_OLLAMA', False)
