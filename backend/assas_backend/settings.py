import os
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent


def _load_env_file(path):
    """Read KEY=VALUE lines from backend/.env (gitignored) into the
    environment, without overriding variables that are already set."""
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        key, value = line.split('=', 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_load_env_file(BASE_DIR / '.env')


def _env_bool(name, default=False):
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in ('1', 'true', 'yes', 'on')


def _env_list(name, default):
    value = os.environ.get(name)
    items = default if value is None else value.split(',')
    return [item.strip() for item in items if item.strip()]

# Secure by default: debug is off, only local hosts are allowed and there is
# no fallback key. Local development sets these in backend/.env (see
# .env.example); a deployment sets them as real environment variables.
DEBUG = _env_bool('DJANGO_DEBUG')

SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY')
if not SECRET_KEY:
    raise ImproperlyConfigured(
        'DJANGO_SECRET_KEY is not set. Copy backend/.env.example to backend/.env '
        'and fill it in, or set it in the environment.'
    )

ALLOWED_HOSTS = _env_list('DJANGO_ALLOWED_HOSTS', ['localhost', '127.0.0.1'])

# HTTPS hardening (what `manage.py check --deploy` asks for). On whenever
# DEBUG is off, so plain-http local development keeps working; set
# DJANGO_HTTPS=False only for a deliberately HTTP-only staging box.
HTTPS = _env_bool('DJANGO_HTTPS', default=not DEBUG)
SECURE_SSL_REDIRECT = HTTPS
SESSION_COOKIE_SECURE = HTTPS
CSRF_COOKIE_SECURE = HTTPS

# HSTS tells browsers to refuse plain http for this many seconds, and they
# cache it - so start at an hour, confirm HTTPS works everywhere, then raise
# DJANGO_HSTS_SECONDS (e.g. 31536000 = one year).
SECURE_HSTS_SECONDS = int(os.environ.get('DJANGO_HSTS_SECONDS', '3600')) if HTTPS else 0
# Opt-in only: these extend HSTS to every subdomain / browser preload lists
# and are very hard to undo.
SECURE_HSTS_INCLUDE_SUBDOMAINS = _env_bool('DJANGO_HSTS_INCLUDE_SUBDOMAINS')
SECURE_HSTS_PRELOAD = _env_bool('DJANGO_HSTS_PRELOAD')

# Behind a reverse proxy / load balancer that terminates TLS, Django sees
# plain http; trust the proxy's X-Forwarded-Proto header (only enable this
# when such a proxy really sits in front, or clients could spoof it).
if _env_bool('DJANGO_BEHIND_PROXY'):
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'corsheaders',
    'core',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'assas_backend.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'assas_backend.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        # Point this at a persistent volume in production.
        'NAME': os.environ.get('DJANGO_DB_PATH', str(BASE_DIR / 'db.sqlite3')),
    }
}

AUTH_USER_MODEL = 'core.User'

AUTHENTICATION_BACKENDS = [
    'core.auth_backend.StudentIDBackend',
    'django.contrib.auth.backends.ModelBackend',
]

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
}

# The app is served same-origin (Django serves the built frontend, Vite
# proxies in development), so CORS is only needed for a separately hosted
# frontend. CSRF_TRUSTED_ORIGINS must list the public https origin, e.g.
# DJANGO_CSRF_TRUSTED_ORIGINS=https://assas.example.edu.my
_LOCAL_ORIGINS = [
    'http://localhost:3000', 'http://127.0.0.1:3000',
    'http://localhost:5173', 'http://127.0.0.1:5173',
]
CORS_ALLOWED_ORIGINS = _env_list('DJANGO_CORS_ALLOWED_ORIGINS', _LOCAL_ORIGINS if DEBUG else [])
CORS_ALLOW_CREDENTIALS = True
CSRF_TRUSTED_ORIGINS = _env_list('DJANGO_CSRF_TRUSTED_ORIGINS', _LOCAL_ORIGINS if DEBUG else [])

# Render sets RENDER_EXTERNAL_HOSTNAME (e.g. assas.onrender.com) on every
# web service, so its own address works without extra configuration.
_RENDER_HOST = os.environ.get('RENDER_EXTERNAL_HOSTNAME')
if _RENDER_HOST:
    ALLOWED_HOSTS.append(_RENDER_HOST)
    CSRF_TRUSTED_ORIGINS.append(f'https://{_RENDER_HOST}')

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Kuala_Lumpur'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATIC_ROOT = Path(os.environ.get('DJANGO_STATIC_ROOT', BASE_DIR / 'staticfiles'))
STORAGES = {
    'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
    'staticfiles': {'BACKEND': 'whitenoise.storage.CompressedStaticFilesStorage'},
}

# The built React app (`npm run build`). WhiteNoise serves its files from the
# site root and core.files.spa_index returns index.html for client routes.
FRONTEND_DIST = Path(os.environ.get('DJANGO_FRONTEND_DIST', BASE_DIR.parent / 'frontend' / 'dist'))
WHITENOISE_ROOT = FRONTEND_DIST if FRONTEND_DIST.is_dir() else None


def _is_hashed_frontend_asset(path, url):
    # Vite fingerprints everything under /assets/ (index-<hash>.js), so
    # browsers can cache those forever; index.html itself stays no-cache.
    return url.startswith('/assets/')


WHITENOISE_IMMUTABLE_FILE_TEST = _is_hashed_frontend_asset

# Uploaded student photos and timetable files. Served only to signed-in
# users through core.files.protected_media - never as public static files.
MEDIA_URL = '/media/'
MEDIA_ROOT = Path(os.environ.get('DJANGO_MEDIA_ROOT', BASE_DIR / 'media'))

# Django's own admin site is a second way in; keep it off in production
# unless it's actually needed.
ENABLE_DJANGO_ADMIN = _env_bool('DJANGO_ENABLE_ADMIN', default=DEBUG)

# Log to stderr, where gunicorn / the hosting platform collects it. With
# DEBUG off, request errors (500s) would otherwise go unseen.
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'plain': {'format': '{asctime} {levelname} {name}: {message}', 'style': '{'},
    },
    'handlers': {
        'console': {'class': 'logging.StreamHandler', 'formatter': 'plain'},
    },
    'root': {'handlers': ['console'], 'level': os.environ.get('DJANGO_LOG_LEVEL', 'INFO')},
    'loggers': {
        'django.request': {'handlers': ['console'], 'level': 'WARNING', 'propagate': False},
        # Bots probing with other Host headers already get a 400; logging a
        # traceback for each would bury real errors.
        'django.security.DisallowedHost': {'handlers': [], 'level': 'CRITICAL', 'propagate': False},
    },
}

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
