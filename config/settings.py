from pathlib import Path
import os
import dj_database_url
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get('SECRET_KEY', '')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.environ.get('DEBUG', 'True') == 'True'

ALLOWED_HOSTS = [
    '127.0.0.1',
    'localhost',
    '0.0.0.0',
    '.onrender.com',
    'synergy-dating.com',
    'www.synergy-dating.com'
]


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Sites framework (required by allauth)
    'django.contrib.sites',

    # Third-party
    'storages',          # S3 / static storage
    'allauth',
    'allauth.account',
    'allauth.socialaccount',

    # Social providers (example: Google – add more later as needed)
    'allauth.socialaccount.providers.google',

    # Local apps
    'website.apps.WebsiteConfig',  # Updated to use app config for signals
]

SITE_ID = 1


MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',  # Static files via WhiteNoise
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',

    # NEW: required by django-allauth
    'allauth.account.middleware.AccountMiddleware',

    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]



ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        # Global templates dir
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                # IMPORTANT for allauth: request processor must be enabled
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                
                # Custom context processor for legal compliance notice
                'website.context_processors.legal_compliance_notice',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'


# Database
# https://docs.djangoproject.com/en/5.2/ref/settings/#databases

if 'RENDER' in os.environ:
    # Production - PostgreSQL on Render
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': os.environ.get('PGDATABASE'),
            'USER': os.environ.get('PGUSER'),
            'PASSWORD': os.environ.get('PGPASSWORD'),
            'HOST': os.environ.get('PGHOST'),
            'PORT': os.environ.get('PGPORT', '5432'),
        }
    }
else:
    # Local development - SQLite
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }


# Password validation
# https://docs.djangoproject.com/en/5.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        # Minimum length set to 10
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {
            'min_length': 10,
        },
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
    # REMOVED: ComplexPasswordValidator that was causing import errors
    # {
    #     'NAME': 'website.validation.ComplexPasswordValidator',
    # },
]


# Authentication backends: Django + allauth
AUTHENTICATION_BACKENDS = [
    # Django's default auth (needed for admin)
    'django.contrib.auth.backends.ModelBackend',
    # allauth authentication
    'allauth.account.auth_backends.AuthenticationBackend',
]


# ==========================
# django-allauth configuration (UPDATED FOR LATEST VERSION)
# ==========================

# Authentication method: username OR email
ACCOUNT_AUTHENTICATION_METHOD = 'username_email'

# Email settings
ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_UNIQUE_EMAIL = True

# Username settings  
ACCOUNT_USERNAME_REQUIRED = False

# Signup fields
ACCOUNT_SIGNUP_FIELDS = ['email*', 'username', 'password1*', 'password2*']

# Rate limiting
ACCOUNT_RATE_LIMITS = {
    'login_failed': '5/5m',
    'signup': '20/1h',
}

# Email verification
ACCOUNT_EMAIL_VERIFICATION = 'optional'

# Login methods
ACCOUNT_LOGIN_METHODS = {'username', 'email'}

# Where to go after login / logout
LOGIN_REDIRECT_URL = '/dashboard/'
ACCOUNT_LOGOUT_REDIRECT_URL = 'index'

# Internationalization
# https://docs.djangoproject.com/en/5.2/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True


# Static and media files
# https://docs.djangoproject.com/en/5.2/howto/static-files/

if 'RENDER' in os.environ:
    # Production - AWS S3
    AWS_ACCESS_KEY_ID = os.environ.get('AWS_ACCESS_KEY_ID')
    AWS_SECRET_ACCESS_KEY = os.environ.get('AWS_SECRET_ACCESS_KEY')
    AWS_STORAGE_BUCKET_NAME = os.environ.get('AWS_STORAGE_BUCKET_NAME')
    AWS_S3_REGION_NAME = os.environ.get('AWS_S3_REGION_NAME', 'us-east-1')
    AWS_S3_CUSTOM_DOMAIN = f'{AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com'
    
    # Static & media over S3
    STATICFILES_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'
    DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'
    
    STATIC_URL = f'https://{AWS_S3_CUSTOM_DOMAIN}/static/'
    MEDIA_URL = f'https://{AWS_S3_CUSTOM_DOMAIN}/media/'
else:
    # Local development - local static/media
    STATIC_URL = '/static/'
    STATIC_ROOT = BASE_DIR / "staticfiles"
    
    STATICFILES_DIRS = [
        BASE_DIR / "static",
    ]
    
    MEDIA_URL = '/media/'
    MEDIA_ROOT = BASE_DIR / "media"
    
    # WhiteNoise configuration for static files
    STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'


# Default primary key field type
# https://docs.djangoproject.com/en/5.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


# ========== BREVO SMTP CONFIGURATION ==========
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp-relay.brevo.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = '9a6c64001@smtp-brevo.com'
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', '')

# ========== IMPORTANT: SENDER CONFIGURATION ==========
# Since you haven't added synergy-dating.com to Brevo yet,
# you MUST use a sender email that's already verified in Brevo

# OPTION A: Use your Brevo SMTP email as sender (WILL WORK NOW)
DEFAULT_FROM_EMAIL = 'Synergy Dating <9a6c64001@smtp-brevo.com>'
SERVER_EMAIL = '9a6c64001@smtp-brevo.com'

# OPTION B: Or use a different verified email from your Brevo account
# DEFAULT_FROM_EMAIL = 'Synergy Dating <your-verified-email@gmail.com>'

# ========== SITE SETTINGS ==========
SITE_NAME = 'Synergy Dating'
SITE_URL = 'https://synergy-dating.com'  # Your website URL

# ========== ADMIN SETTINGS ==========
ADMINS = [
    ('Admin', 'admin@synergy-dating.com'),
]
MANAGERS = ADMINS

# =============================================================================
# LEGAL COMPLIANCE SETTINGS
# =============================================================================

# Message retention policy (in days, 0 = forever)
MESSAGE_RETENTION_DAYS = 0  # LEGAL REQUIREMENT: Store forever

# Activity logging
ACTIVITY_LOGGING_ENABLED = True

# Admin email for legal compliance notifications
LEGAL_COMPLIANCE_EMAIL = os.environ.get('LEGAL_COMPLIANCE_EMAIL', 'legal@synergy-dating.com')
ADMIN_EMAILS = ['admin@synergy-dating.com']

# Data export settings
DATA_EXPORT_ENABLED = True
MAX_EXPORT_RECORDS = 10000  # Limit for single export

# =============================================================================
# SECURITY SETTINGS (Auto-configured for production)
# =============================================================================

if 'RENDER' in os.environ:
    # Production security settings
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 31536000  # 1 year
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
else:
    # Local development security settings
    SECURE_SSL_REDIRECT = False
    SESSION_COOKIE_SECURE = False
    CSRF_COOKIE_SECURE = False
    SECURE_HSTS_SECONDS = 0
    SECURE_BROWSER_XSS_FILTER = False
    SECURE_CONTENT_TYPE_NOSNIFF = False


# Environment detection logs (for your console)
if 'RENDER' in os.environ:
    print("🚀 PRODUCTION SETTINGS LOADED")
else:
    print("🔧 LOCAL DEVELOPMENT SETTINGS LOADED")

print(f"DEBUG = {DEBUG}")
print(f"ALLOWED_HOSTS = {ALLOWED_HOSTS}")
print(f"DATABASE = {'PostgreSQL' if 'RENDER' in os.environ else 'SQLite'}")
print(f"STATIC FILES = {'AWS S3' if 'RENDER' in os.environ else 'Local'}")

# LEGAL COMPLIANCE MODE ACTIVE
print("⚖️ LEGAL COMPLIANCE MODE: ACTIVE")
print(f"  • Message Retention: {'FOREVER' if MESSAGE_RETENTION_DAYS == 0 else f'{MESSAGE_RETENTION_DAYS} days'}")
print(f"  • Activity Logging: {'ENABLED' if ACTIVITY_LOGGING_ENABLED else 'DISABLED'}")
print(f"  • Data Export: {'ENABLED' if DATA_EXPORT_ENABLED else 'DISABLED'}")
