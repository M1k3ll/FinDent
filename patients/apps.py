from django.apps import AppConfig
from django.db.models.signals import post_migrate


def create_default_groups(sender, **kwargs):
    """گروه‌های پیش‌فرض «منشی» و «دکتر» را می‌سازد و دسترسی‌های پایه را تضمین می‌کند.

    فقط دسترسی اضافه می‌شود (add، نه set)، پس اجرای دوباره‌ی migrate هیچ‌وقت
    دسترسی‌ای را که خودت بعداً به این گروه‌ها اضافه کرده‌ای پاک نمی‌کند؛ فقط
    مطمئن می‌شود این فهرست پایه همیشه وجود دارد (مثلاً بعد از اضافه شدن مدل عکس).
    """
    from django.contrib.auth.models import Group, Permission

    definitions = {
        "منشی": [
            "view_patient", "add_patient", "change_patient",
            "view_visit", "add_visit", "change_visit",
            "view_patientphoto", "add_patientphoto",
        ],
        "دکتر": [
            "view_patient", "add_patient", "change_patient",
            "view_visit", "add_visit", "change_visit", "delete_visit",
            "view_patientphoto", "add_patientphoto", "delete_patientphoto",
            "view_auditlog",
        ],
    }
    for name, codes in definitions.items():
        group, _ = Group.objects.get_or_create(name=name)
        group.permissions.add(
            *Permission.objects.filter(content_type__app_label="patients", codename__in=codes)
        )


class PatientsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "patients"
    verbose_name = "پرونده بیماران"

    def ready(self):
        from . import signals  # noqa: F401

        post_migrate.connect(create_default_groups, sender=self, dispatch_uid="findent_default_groups")
