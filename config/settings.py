"""تنظیمات Findent: سرور محلی جنگو با دیتابیس SQLite برای یک مطب."""
import os
from pathlib import Path

from django.core.management.utils import get_random_secret_key

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"  # دیتابیس، لاگ‌ها و کلید امنیتی اینجا هستند
DATA_DIR.mkdir(exist_ok=True)

# کلید امنیتی یک بار ساخته می‌شود و در data/secret_key.txt می‌ماند
_key_file = DATA_DIR / "secret_key.txt"
if os.environ.get("FINDENT_SECRET_KEY"):
    SECRET_KEY = os.environ["FINDENT_SECRET_KEY"]
else:
    if not _key_file.exists():
        _key_file.write_text(get_random_secret_key())
    SECRET_KEY = _key_file.read_text().strip()

DEBUG = os.environ.get("FINDENT_DEBUG") == "1"

# برای استفاده روی شبکه‌ی مطب: set FINDENT_ALLOWED_HOSTS=192.168.1.10
ALLOWED_HOSTS = ["localhost", "127.0.0.1", "[::1]"] + [
    h.strip() for h in os.environ.get("FINDENT_ALLOWED_HOSTS", "").split(",") if h.strip()
]

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
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
     "OPTIONS": {"min_length": 6}},
]

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

LANGUAGE_CODE = "fa"
TIME_ZONE = "Asia/Tehran"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"
WHITENOISE_USE_FINDERS = True

# عکس‌های بیماران اینجا ذخیره می‌شوند؛ فقط از طریق ویوی patient_photo_file
# (که ورود و دسترسی را چک می‌کند) قابل دیدن‌اند، نه با آدرس مستقیم.
MEDIA_ROOT = DATA_DIR / "media"
MEDIA_URL = "media/"  # مستقیماً استفاده نمی‌شود؛ فقط برای کامل بودن تنظیمات جنگو
FILE_UPLOAD_MAX_MEMORY_SIZE = 15 * 1024 * 1024  # ۱۵ مگابایت

STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedStaticFilesStorage"},
}

LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "home"
LOGOUT_REDIRECT_URL = "login"
SESSION_COOKIE_AGE = 60 * 60 * 12  # ۱۲ ساعت

# بکاپ محلیِ روزانه‌ی دیتابیس. پیش‌فرض یک پوشه کنار پروژه است؛ اگر هارد یا فلش
# دیگری در کامپیوتر مطب هست، بهتر است FINDENT_BACKUP_DIR را به آنجا اشاره بدهی
# (مثلاً در Task Scheduler، Environment: FINDENT_BACKUP_DIR=D:\Findent-Backups)
BACKUP_DIR = Path(os.environ.get("FINDENT_BACKUP_DIR", str(BASE_DIR / "backups")))
BACKUP_KEEP = int(os.environ.get("FINDENT_BACKUP_KEEP", "30"))  # چند نسخه‌ی آخر نگه داشته شود

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {"std": {"format": "%(asctime)s %(levelname)s %(name)s: %(message)s"}},
    "handlers": {
        "file": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": str(DATA_DIR / "findent.log"),
            "maxBytes": 1_000_000,
            "backupCount": 3,
            "encoding": "utf-8",
            "formatter": "std",
        },
    },
    "root": {"handlers": ["file"], "level": "WARNING"},
}
