
# core/settings.py
import os
from pathlib import Path
from dotenv import load_dotenv
import dj_database_url

load_dotenv()  # Load environment variables

BASE_DIR = Path(__file__).resolve().parent.parent

# Use environment variable for secret key with fallback
SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')

# Debug mode based on environment
DEBUG = os.environ.get('DEBUG', 'True').lower() == 'true'

# Brevo
BREVO_API_KEY = os.environ.get('BREVO_API_KEY', 'dev-key-placeholder') 
DEFAULT_FROM_EMAIL = 'GR8DATE <hello@gr8date.com.au>'  # Change to your domain

# ADD SITE DOMAIN FOR SITEMAP 
SITE_DOMAIN = os.environ.get('SITE_DOMAIN', 'gr8date.com.au')

# CSRF and Allowed Hosts for Render
CSRF_TRUSTED_ORIGINS = [
    'https://*.onrender.com',
    'http://*.onrender.com',
    'http://127.0.0.1:8000',
    'http://localhost:8000',
    'https://gr8date.com.au',  # REMOVED f-string - just use plain strings
    'https://www.gr8date.com.au',  
]

ALLOWED_HOSTS = [
    'gr8date.onrender.com', 
    '.onrender.com', 
    'gr8date.com.au',
    '.gr8date.com.au',
    'www.gr8date.com.au',
    'localhost', 
    '127.0.0.1'
]

# ======================
# SESSION SECURITY - WORKS LOCALLY & IN PRODUCTION
# ======================

# Session expiration
SESSION_EXPIRE_AT_BROWSER_CLOSE = True  # Users logout on browser close
SESSION_COOKIE_AGE = 86400  # 24 hours maximum session length
SESSION_SAVE_EVERY_REQUEST = True  # Extend session with user activity

# Security headers (auto-adjust for environment)
SESSION_COOKIE_HTTPONLY = True  # Prevent JavaScript access to session cookie
SESSION_COOKIE_SECURE = not DEBUG  # HTTPS only in production
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SECURE = not DEBUG  # HTTPS only in production


# FIX: Update security settings to work in both dev and production
if not DEBUG:
    # Production settings
    SECURE_SSL_REDIRECT = True
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    USE_X_FORWARDED_HOST = True
else:
    # Development settings - allow HTTP
    SESSION_COOKIE_SECURE = False
    CSRF_COOKIE_SECURE = False


# Database configuration
DATABASES = {
    'default': dj_database_url.config(
        default='sqlite:///db.sqlite3',
        conn_max_age=600,
        conn_health_checks=True,
    )
}

# If on Render, ensure we use PostgreSQL
if 'RENDER' in os.environ:
    DATABASES['default'] = dj_database_url.config(
        conn_max_age=600,
        conn_health_checks=True,
    )

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites',
    'django.contrib.sitemaps',  # ✅ ALREADY ADDED
    'pages',
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'blog',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'allauth.account.middleware.AccountMiddleware',
]

ROOT_URLCONF = 'core.urls'

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

WSGI_APPLICATION = 'core.wsgi.application'

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {
            'min_length': 12,  # Changed from 8 to 12
        }
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# Static files configuration
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

# Media files
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# WhiteNoise configuration for static files
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

SITE_ID = 1

# Allauth configuration
AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
    'allauth.account.auth_backends.AuthenticationBackend',
]

# Allauth settings
ACCOUNT_EMAIL_VERIFICATION = 'none'
ACCOUNT_LOGIN_METHODS = {'email', 'username'}
ACCOUNT_SIGNUP_FIELDS = ['email*', 'username*', 'password1*', 'password2*']
ACCOUNT_LOGOUT_ON_GET = True

LOGIN_URL = '/accounts/login/'
LOGIN_REDIRECT_URL = '/dashboard/'
LOGOUT_REDIRECT_URL = '/'

# Add this for production security
if not DEBUG:
    SECURE_SSL_REDIRECT = True
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    # ADD FOR PRODUCTION SITEMAP
    USE_X_FORWARDED_HOST = True

# Use your custom template instead of allauth's default
ACCOUNT_FORMS = {
    'login': 'pages.forms.CustomLoginForm',
}

# Serve media files from static during deployment
if not DEBUG:
    # In production, serve media from static
    MEDIA_URL = '/static/media/'
else:
    MEDIA_URL = '/media/'

# ⭐⭐⭐ ADD THIS SECTION AT THE BOTTOM ⭐⭐⭐
# UPDATE SITE DOMAIN FOR SITEMAP - THIS IS WHAT FIXES example.com
try:
    from django.contrib.sites.models import Site
    site = Site.objects.get(id=SITE_ID)
    if DEBUG:
        site.domain = '127.0.0.1:8000'
        site.name = 'GR8Date (Development)'
    else:
        site.domain = 'gr8date.com.au'
        site.name = 'GR8Date - Free Dating Australia'
    site.save()
except:
    # This might fail during initial migrations, that's okay
    pass
