"""Findent: تنظیمات پروژه (اجرای محلی روی یک کامپیوتر مطب)."""
import os
from pathlib import Path

from django.core.management.utils import get_random_secret_key

BASE_DIR = Path(__file__).resolve().parent.parent

# همه‌ی داده‌ها (دیتابیس، کلید امنیتی، لاگ) در پوشه‌ی data نگهداری می‌شود.
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)


def _load_secret_key():
    key_file = DATA_DIR / "secret_key.txt"
    if key_file.exists():
        return key_file.read_text(encoding="utf-8").strip()
    key = get_random_secret_key()
    key_file.write_text(key, encoding="utf-8")
    return key


SECRET_KEY = _load_secret_key()

DEBUG = os.environ.get("FINDENT_DEBUG", "0") == "1"

# برای استفاده در شبکه‌ی داخلی، آدرس کامپیوتر را با متغیر محیطی اضافه کنید.
ALLOWED_HOSTS = ["localhost", "127.0.0.1", "[::1]"] + [
    h.strip() for h in os.environ.get("FINDENT_ALLOWED_HOSTS", "").split(",") if h.strip()
]

# اعتبارسنجی الگوریتمی کدملی. برای بیماران اتباع خارجی می‌توانید 0 بگذارید.
FINDENT_STRICT_NATIONAL_ID = os.environ.get("FINDENT_STRICT_NATIONAL_ID", "1") == "1"

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "patients",
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

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "patients.context_processors.site_credit",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": DATA_DIR / "db.sqlite3",
        "OPTIONS": {"timeout": 20},
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 8},
    },
]

LANGUAGE_CODE = "fa"
TIME_ZONE = "Asia/Tehran"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"
WHITENOISE_USE_FINDERS = True

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "home"
LOGOUT_REDIRECT_URL = "login"

# خروج خودکار پس از ۱۲ ساعت
SESSION_COOKIE_AGE = 60 * 60 * 12

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "file": {
            "class": "logging.FileHandler",
            "filename": str(DATA_DIR / "findent.log"),
            "encoding": "utf-8",
        },
    },
    "loggers": {"django": {"handlers": ["file"], "level": "WARNING"}},
}
