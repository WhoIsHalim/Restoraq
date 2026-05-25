from __future__ import annotations

import importlib.util
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]


def env(name: str, default=None):
    return os.getenv(name, default)


def env_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def env_list(name: str, default: str = "") -> list[str]:
    raw = os.getenv(name, default)
    return [item.strip() for item in raw.split(",") if item.strip()]


def has_module(module_name: str) -> bool:
    try:
        return importlib.util.find_spec(module_name) is not None
    except ModuleNotFoundError:
        return False


DEBUG = env_bool("DEBUG", False)
SECRET_KEY = env("SECRET_KEY")
if not SECRET_KEY:
    settings_module = os.getenv("DJANGO_SETTINGS_MODULE", "")
    if DEBUG or settings_module.endswith(".dev"):
        SECRET_KEY = "unsafe-development-secret-key"
    else:
        raise RuntimeError("SECRET_KEY is required in production settings.")

ALLOWED_HOSTS = env_list("ALLOWED_HOSTS", "localhost,127.0.0.1")
CSRF_TRUSTED_ORIGINS = env_list("CSRF_TRUSTED_ORIGINS", "http://localhost:8000")

THIRD_PARTY_APPS = []
if has_module("django_celery_beat"):
    THIRD_PARTY_APPS.append("django_celery_beat")
if has_module("django_celery_results"):
    THIRD_PARTY_APPS.append("django_celery_results")
if has_module("axes"):
    THIRD_PARTY_APPS.append("axes")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.humanize",
    *THIRD_PARTY_APPS,
    "core",
    "accounts",
    "tenants",
    "subscriptions",
    "restaurants",
    "users",
    "pos",
    "orders",
    "menu",
    "inventory",
    "reports",
    "crm",
    "hr",
    "printing",
    "audit",
    "backup",
    "support",
    "featureflags",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
]
if has_module("whitenoise"):
    MIDDLEWARE.append("whitenoise.middleware.WhiteNoiseMiddleware")
MIDDLEWARE += [
    "django.contrib.sessions.middleware.SessionMiddleware",
    "core.middleware.ContentSecurityPolicyMiddleware",
    "core.middleware.DefaultLanguageCookieMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
]
if "axes" in THIRD_PARTY_APPS:
    MIDDLEWARE.append("axes.middleware.AxesMiddleware")
MIDDLEWARE += [
    "core.middleware.RequestContextMiddleware",
    "tenants.middleware.TenantResolutionMiddleware",
    "tenants.middleware.TenantDBContextMiddleware",
    "subscriptions.middleware.SubscriptionAccessMiddleware",
    "accounts.middleware.SessionTimeoutMiddleware",
    "audit.middleware.AuditContextMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "libraries": {
                "admin_pagination": "core.templatetags.admin_pagination",
            },
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "core.context_processors.layout_context",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

DB_ENGINE = env("DB_ENGINE", "django.db.backends.sqlite3")
if DB_ENGINE.endswith("sqlite3"):
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": DB_ENGINE,
            "NAME": env("DB_NAME", "restaurant_saas"),
            "USER": env("DB_USER", "postgres"),
            "PASSWORD": env("DB_PASSWORD", "postgres"),
            "HOST": env("DB_HOST", "127.0.0.1"),
            "PORT": env("DB_PORT", "5432"),
            "CONN_MAX_AGE": 60,
        }
    }

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher",
    "django.contrib.auth.hashers.BCryptSHA256PasswordHasher",
]
if has_module("argon2"):
    PASSWORD_HASHERS.insert(0, "django.contrib.auth.hashers.Argon2PasswordHasher")

LANGUAGE_CODE = env("DEFAULT_LANGUAGE", "ar")
LANGUAGES = (
    ("ar", "Arabic"),
    ("en", "English"),
)
LANGUAGE_COOKIE_NAME = env("LANGUAGE_COOKIE_NAME", "django_language")
LANGUAGE_COOKIE_SAMESITE = env("LANGUAGE_COOKIE_SAMESITE", "Strict")
LANGUAGE_COOKIE_SECURE = env_bool("LANGUAGE_COOKIE_SECURE", False if DEBUG else True)
LOCALE_PATHS = [BASE_DIR / "locale"]

TIME_ZONE = env("TIME_ZONE", "Africa/Cairo")
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]
if has_module("whitenoise"):
    STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
AUTH_USER_MODEL = "accounts.User"
LOGIN_URL = "accounts:login"
LOGIN_REDIRECT_URL = "core:dashboard"
LOGOUT_REDIRECT_URL = "accounts:login"

# Hidden entry points for admin/system consoles (use non-guessable paths in production).
ADMIN_PATH = env("ADMIN_PATH", "secure-admin/")
SYSTEM_PATH = env("SYSTEM_PATH", "secure-system/")

if "axes" in THIRD_PARTY_APPS:
    AXES_FAILURE_LIMIT = 5
    AXES_COOLOFF_TIME = 1
    AXES_LOCKOUT_PARAMETERS = ["username", "ip_address"]

SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Strict"
CSRF_COOKIE_SAMESITE = "Strict"

SECURE_SSL_REDIRECT = env_bool("SECURE_SSL_REDIRECT", True)
SESSION_COOKIE_SECURE = env_bool("SESSION_COOKIE_SECURE", True)
CSRF_COOKIE_SECURE = env_bool("CSRF_COOKIE_SECURE", True)
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
SECURE_CROSS_ORIGIN_OPENER_POLICY = "same-origin"
X_FRAME_OPTIONS = "DENY"

CONTENT_SECURITY_POLICY = env(
    "CONTENT_SECURITY_POLICY",
    "default-src 'self'; "
    "base-uri 'self'; "
    "form-action 'self'; "
    "frame-ancestors 'none'; "
    "object-src 'none'; "
    "img-src 'self' data: https:; "
    "font-src 'self' https://fonts.gstatic.com; "
    "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://cdn.jsdelivr.net https://cdnjs.cloudflare.com; "
    "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com; "
    "connect-src 'self';"
)

TENANT_HEADER_NAME = env("TENANT_HEADER_NAME", "HTTP_X_TENANT")
TENANT_HEADER_SIGNATURE_SECRET = env("TENANT_HEADER_SIGNATURE_SECRET", SECRET_KEY)

CELERY_BROKER_URL = env("REDIS_URL", "redis://127.0.0.1:6379/0")
CELERY_RESULT_BACKEND = "django-db" if "django_celery_results" in THIRD_PARTY_APPS else None
CELERY_CACHE_BACKEND = "django-cache"
CELERY_TIMEZONE = TIME_ZONE
if "django_celery_beat" in THIRD_PARTY_APPS:
    CELERY_BEAT_SCHEDULER = "django_celery_beat.schedulers:DatabaseScheduler"

if has_module("celery.schedules"):
    from celery.schedules import crontab

    CELERY_BEAT_SCHEDULE = {
        "daily-db-backup": {
            "task": "backup.tasks.daily_backup_task",
            "schedule": crontab(hour=3, minute=0),
        },
        "retry-print-jobs": {
            "task": "printing.tasks.retry_failed_print_jobs",
            "schedule": crontab(minute="*/2"),
        },
        "detect-low-stock": {
            "task": "inventory.tasks.detect_low_stock_alerts",
            "schedule": crontab(minute="*/10"),
        },
        "cleanup-audit-logs": {
            "task": "audit.tasks.cleanup_old_audit_logs",
            "schedule": crontab(hour=4, minute=0, day_of_month="1"),
        },
    }

BACKUP_LOCAL_DIR = env("BACKUP_LOCAL_DIR", str(BASE_DIR / "backups"))
BACKUP_S3_PREFIX = env("BACKUP_S3_PREFIX", "postgres")

AWS_S3_ENABLED = env_bool("AWS_S3_ENABLED", False)
AWS_STORAGE_BUCKET_NAME = env("AWS_STORAGE_BUCKET_NAME", "")
AWS_S3_REGION_NAME = env("AWS_S3_REGION_NAME", "eu-central-1")
AWS_ACCESS_KEY_ID = env("AWS_ACCESS_KEY_ID", "")
AWS_SECRET_ACCESS_KEY = env("AWS_SECRET_ACCESS_KEY", "")

if AWS_S3_ENABLED and has_module("storages"):
    DEFAULT_FILE_STORAGE = "storages.backends.s3boto3.S3Boto3Storage"

REDIS_URL = env("REDIS_URL", "redis://127.0.0.1:6379/1")
if has_module("redis"):
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.redis.RedisCache",
            "LOCATION": REDIS_URL,
        }
    }
else:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "restoraq",
        }
    }

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {"class": "logging.StreamHandler"},
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
}

AUDIT_RETENTION_DAYS = int(env('AUDIT_RETENTION_DAYS', '730'))
