"""
بکاپ محلی روزانه از دیتابیس DentiX.

اجرا: python manage.py backup_local
هر بار یک کپی سالم و امن از دیتابیس (حتی اگر همان لحظه کسی در حال کار با
برنامه باشد) در پوشه‌ی BACKUP_DIR می‌سازد و نسخه‌های قدیمی‌تر از BACKUP_KEEP
تا آخرین نسخه را پاک می‌کند.

از sqlite3 backup API استفاده می‌کند (نه فقط کپی فایل)، چون کپی خام فایل
ممکن است وسط یک نوشتن گرفته شود و خراب باشد؛ backup API این را تضمین می‌کند.
"""
import sqlite3
from datetime import datetime
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "یک بکاپ سالم از دیتابیس می‌سازد و نسخه‌های قدیمی اضافه را پاک می‌کند."

    def handle(self, *args, **options):
        src_path = Path(settings.DATABASES["default"]["NAME"])
        backup_dir = Path(settings.BACKUP_DIR)
        backup_dir.mkdir(parents=True, exist_ok=True)

        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        dest_path = backup_dir / f"findent-{stamp}.sqlite3"

        src = sqlite3.connect(str(src_path))
        dest = sqlite3.connect(str(dest_path))
        with dest:
            src.backup(dest)
        src.close()
        dest.close()

        self.stdout.write(self.style.SUCCESS(f"بکاپ ساخته شد: {dest_path}"))

        # پاک کردن نسخه‌های اضافه، فقط قدیمی‌ترین‌ها
        backups = sorted(backup_dir.glob("findent-*.sqlite3"), key=lambda p: p.name)
        extra = backups[: max(0, len(backups) - settings.BACKUP_KEEP)]
        for old in extra:
            old.unlink()
        if extra:
            self.stdout.write(f"{len(extra)} نسخه‌ی قدیمی پاک شد.")
