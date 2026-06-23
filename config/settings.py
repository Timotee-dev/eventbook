import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# ── Read .env file manually (no python-decouple needed) ──
def env(key, default=''):
    val = os.environ.get(key, default)
    if not val:
        env_file = BASE_DIR / '.env'
        if env_file.exists():
            for line in env_file.read_text().splitlines():
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    k, _, v = line.partition('=')
                    if k.strip() == key:
                        return v.strip().strip('"').strip("'")
    return val

def env_bool(key, default=False):
    return env(key, str(default)).lower() in ('true', '1', 'yes')

SECRET_KEY = env('SECRET_KEY', 'django-insecure-eventbook-change-in-production-xyz123')
DEBUG = env_bool('DEBUG', True)

# ── Allow all hosts — handles any Render URL automatically ──
ALLOWED_HOSTS = ['*']

SITE_NAME = env('SITE_NAME', 'EventBook')
FRONTEND_URL = env('FRONTEND_URL', 'http://localhost:8000')

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'apps.core',
    'apps.accounts',
    'apps.events',
    'apps.bookings',
    'apps.payments',
    'apps.tickets',
    'apps.reviews',
    'apps.notifications',
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
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [{
    'BACKEND': 'django.template.backends.django.DjangoTemplates',
    'DIRS': [BASE_DIR / 'templates'],
    'APP_DIRS': True,
    'OPTIONS': {
        'context_processors': [
            'django.template.context_processors.debug',
            'django.template.context_processors.request',
            'django.contrib.auth.context_processors.auth',
            'django.contrib.messages.context_processors.messages',
            'apps.core.context_processors.site_settings',
        ],
    },
}]

WSGI_APPLICATION = 'config.wsgi.application'

# ── Database: SQLite by default, Postgres on Render ──
DATABASE_URL = env('DATABASE_URL', '')
if DATABASE_URL:
    import urllib.parse as up
    url = up.urlparse(DATABASE_URL)
    DATABASES = {'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': url.path[1:],
        'USER': url.username,
        'PASSWORD': url.password,
        'HOST': url.hostname,
        'PORT': url.port or 5432,
    }}
else:
    DATABASES = {'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }}

AUTH_USER_MODEL = 'accounts.User'
LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/dashboard/'
LOGOUT_REDIRECT_URL = '/'

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator', 'OPTIONS': {'min_length': 8}},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = env('TIME_ZONE', 'Africa/Lagos')
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

SESSION_ENGINE = 'django.contrib.sessions.backends.db'
SESSION_COOKIE_AGE = 60 * 60 * 24 * 14  # 2 weeks
SESSION_COOKIE_SECURE = not DEBUG

# ── Email ──
EMAIL_BACKEND = env('EMAIL_BACKEND', 'django.core.mail.backends.console.EmailBackend')
EMAIL_HOST = env('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = int(env('EMAIL_PORT', '587'))
EMAIL_USE_TLS = True
EMAIL_HOST_USER = env('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = env('EMAIL_HOST_PASSWORD', '')
DEFAULT_FROM_EMAIL = env('DEFAULT_FROM_EMAIL', 'EventBook <noreply@eventbook.ng>')

# ── Paystack (real transactions) ──
PAYSTACK_SECRET_KEY = env('PAYSTACK_SECRET_KEY', '')
PAYSTACK_PUBLIC_KEY = env('PAYSTACK_PUBLIC_KEY', '')
PAYSTACK_BASE_URL = 'https://api.paystack.co'
PLATFORM_FEE_PERCENT = int(env('PLATFORM_FEE_PERCENT', '5'))

# ── Security ──
if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SECURE_SSL_REDIRECT = False
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_CONTENT_TYPE_NOSNIFF = True

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {'console': {'class': 'logging.StreamHandler'}},
    'root': {'handlers': ['console'], 'level': 'INFO'},
    'loggers': {'apps': {'handlers': ['console'], 'level': 'DEBUG', 'propagate': False}},
}

os.makedirs(BASE_DIR / 'logs', exist_ok=True)
os.makedirs(BASE_DIR / 'media', exist_ok=True)