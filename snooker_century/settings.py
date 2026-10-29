"""
Django settings for the Snooker Century project.

Configuration is read from environment variables so no secrets live in the repo.
See .env.example for the full list.
"""
import os
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured

try:  # python-dotenv is optional (handy for local development)
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:  # pragma: no cover
    pass

BASE_DIR = Path(__file__).resolve().parent.parent


def env_bool(name, default=False):
    return os.getenv(name, str(default)).strip().lower() in {"1", "true", "yes", "on"}


def env_list(name):
    return [item.strip() for item in os.getenv(name, "").split(",") if item.strip()]


# --- Core security -----------------------------------------------------------
DEBUG = env_bool("DEBUG", False)

SECRET_KEY = os.getenv("DJANGO_SECRET_KEY") or os.getenv("SECRET_KEY")
if not SECRET_KEY:
    if DEBUG:
        SECRET_KEY = "django-insecure-local-development-only"
    else:
        raise ImproperlyConfigured(
            "Set the DJANGO_SECRET_KEY environment variable (e.g. in your Vercel project settings)."
        )

ALLOWED_HOSTS = [".vercel.app", "localhost", "127.0.0.1", "[::1]"] + env_list("ALLOWED_HOSTS")
CSRF_TRUSTED_ORIGINS = ["https://*.vercel.app"] + env_list("CSRF_TRUSTED_ORIGINS")

if not DEBUG:
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SECURE_REFERRER_POLICY = "same-origin"

# --- Applications ------------------------------------------------------------
INSTALLED_APPS = [
    "whitenoise.runserver_nostatic",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "accounts",
    "matches",
    "stats",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "snooker_century.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        # Project-wide templates live in /templates (NOT in /static, which is public).
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "snooker_century.wsgi.application"

# --- Database ----------------------------------------------------------------
# Production (Vercel): set the database_* variables. Local dev: falls back to SQLite.
if os.getenv("database_engine"):
    DATABASES = {
        "default": {
            "ENGINE": os.getenv("database_engine"),
            "NAME": os.getenv("database_name"),
            "USER": os.getenv("database_user"),
            "PASSWORD": os.getenv("database_password"),
            "HOST": os.getenv("database_host"),
            "PORT": os.getenv("database_port", ""),
            "OPTIONS": ({"sslmode": os.getenv("database_sslmode")} if os.getenv("database_sslmode") else {}),
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

# --- Auth --------------------------------------------------------------------
AUTH_USER_MODEL = "accounts.User"
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]
LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "dashboard"
LOGOUT_REDIRECT_URL = "login"

# --- i18n --------------------------------------------------------------------
LANGUAGE_CODE = "en-us"
TIME_ZONE = os.getenv("TIME_ZONE", "UTC")
USE_I18N = True
USE_TZ = True

# --- Static & media ----------------------------------------------------------
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]

STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedStaticFilesStorage"},
}

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# Bootstrap-friendly message tags (Django's "error" is Bootstrap's "danger")
from django.contrib.messages import constants as message_constants  # noqa: E402

MESSAGE_TAGS = {message_constants.ERROR: "danger"}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# --- Cache & sessions --------------------------------------------------------
REDIS_URL = os.getenv("REDIS_URL")
if REDIS_URL:
    REDIS_CACHE_OPTIONS = {"CLIENT_CLASS": "django_redis.client.DefaultClient"}
    CACHES = {
        "default": {
            "BACKEND": "django_redis.cache.RedisCache",
            "LOCATION": REDIS_URL,
            "KEY_PREFIX": "snooker-century:cache",
            "TIMEOUT": 300,
            "OPTIONS": REDIS_CACHE_OPTIONS,
        },
        "sessions": {
            "BACKEND": "django_redis.cache.RedisCache",
            "LOCATION": os.getenv("REDIS_SESSION_URL") or REDIS_URL,
            "KEY_PREFIX": "snooker-century:sessions",
            "OPTIONS": REDIS_CACHE_OPTIONS,
        },
    }
    SESSION_ENGINE = "django.contrib.sessions.backends.cache"
    SESSION_CACHE_ALIAS = "sessions"
else:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "snooker-century",
            "TIMEOUT": 300,
        }
    }
    SESSION_ENGINE = "django.contrib.sessions.backends.db"
