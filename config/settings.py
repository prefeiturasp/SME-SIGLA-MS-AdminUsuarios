from pathlib import Path
import os
from dotenv import load_dotenv

load_dotenv()

DJANGO_ENVIRONMENT = os.environ.get('DJANGO_ENVIRONMENT', 'local')
MS_PATH = os.environ.get('MS_PATH', '/ms-admin-usuarios')

BASE_DIR = Path(__file__).resolve().parent.parent
SECRET_KEY = os.environ.get('SECRET_KEY', 'django-insecure-your-secret-key-here')
DEBUG = os.environ.get('DEBUG', 'True').lower() == 'true'
# ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', '*').split(',')
ALLOWED_HOSTS = ['localhost', '127.0.0.1', '0.0.0.0', 'qa-api-sigla.sme.prefeitura.sp.gov.br']
CSRF_TRUSTED_ORIGINS = ['https://qa-api-sigla.sme.prefeitura.sp.gov.br']

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'rest_framework_simplejwt',
    'corsheaders',
    'drf_spectacular',
    'usuarios',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
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
        'DIRS': [os.path.join(BASE_DIR, 'templates')],
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

# Database
DB_ENGINE = os.environ.get('DB_ENGINE', 'django.db.backends.postgresql')

if DB_ENGINE == 'django.db.backends.sqlite3':
    DATABASES = {
        'default': {
            'ENGINE': DB_ENGINE,
            'NAME': os.environ.get('DB_NAME', BASE_DIR / 'db_sigla.sqlite3'),
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': DB_ENGINE,
            'NAME': os.environ.get('DB_NAME', 'db_sigla'),
            'USER': os.environ.get('DB_USER', 'postgres'),
            'PASSWORD': os.environ.get('DB_PASSWORD', 'postgres'),
            'HOST': os.environ.get('DB_HOST', 'localhost'),
            'PORT': os.environ.get('DB_PORT', '5432'),
        }
    }

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
LANGUAGE_CODE = 'pt-br'
TIME_ZONE = 'America/Sao_Paulo'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
# Em QA/prod o app fica atrás de um path (MS_PATH); STATIC_URL/MEDIA_URL precisam bater com o urlconf.
_ms_path_segment = (MS_PATH or '/ms-admin-usuarios').strip('/')
if DJANGO_ENVIRONMENT != 'local':
    STATIC_URL = f'/{_ms_path_segment}/django_static/'
    MEDIA_URL = f'/{_ms_path_segment}/media/'
else:
    STATIC_URL = '/django_static/'
    MEDIA_URL = '/media/'

# Media files (uploads)
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

REST_FRAMEWORK = {
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 10,
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
        'rest_framework.authentication.TokenAuthentication',
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
}

# CORS settings
CORS_ALLOW_ALL_ORIGINS = True
CORS_ALLOW_CREDENTIALS = True

# External services configuration
# EXTERNAL_SERVICES = {
#     'auth_service': {
#         'base_url': os.environ.get('AUTH_SERVICE_BASE_URL', 'http://localhost:8100'),
#         'timeout': int(os.environ.get('AUTH_SERVICE_TIMEOUT', '10')),
#     },
#     'user_service': {
#         'base_url': os.environ.get('USER_SERVICE_BASE_URL', 'http://localhost:8101'),
#         'timeout': int(os.environ.get('USER_SERVICE_TIMEOUT', '10')),
#     },
# }

SPECTACULAR_SETTINGS = {
    'TITLE': 'Admin Usuarios Sigla API',
    'DESCRIPTION': 'API para o sistema de administração de usuários de sigla',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
}

CORESSO_API_TOKEN = os.environ.get('CORESSO_API_TOKEN', '')
CORESSO_API_URL = os.environ.get('CORESSO_API_URL', '')
SME_INTEGRACAO_URL = os.environ.get('SME_INTEGRACAO_URL', '')
SME_INTEGRACAO_TOKEN = os.environ.get('SME_INTEGRACAO_TOKEN', '')


# E-mail
EMAIL_BACKEND = os.environ.get(
    'EMAIL_BACKEND',
    os.environ.get('DJANGO_EMAIL_BACKEND', 'django.core.mail.backends.console.EmailBackend'),
)
EMAIL_HOST = os.environ.get('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = int(os.environ.get('EMAIL_PORT', '587'))
EMAIL_USE_TLS = os.environ.get('EMAIL_USE_TLS', 'true').lower() == 'true'
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', '')
DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', EMAIL_HOST_USER or 'noreply@localhost')

APLICACAO_URL = os.environ.get('APLICACAO_URL', '')
MS_URL = os.environ.get('MS_URL', '')
