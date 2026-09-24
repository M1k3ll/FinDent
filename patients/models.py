from django.conf import settings
from django.db import IntegrityError, models, transaction
from django.db.models import Max
from django.utils import timezone

from .jalali import jalali_age
from .utils import normalize_text, search_key


class Patient(models.Model):
    file_number = models.PositiveIntegerField("شماره پرونده", unique=True, editable=False)
    first_name = models.CharField("نام", max_length=60)
    last_name = models.CharField("نام خانوادگی", max_length=80)
    national_id = models.CharField("کدملی", max_length=20, unique=True)
    mobile = models.CharField("موبایل", max_length=11)
    birth_date = models.DateField("تاریخ تولد", null=True, blank=True)
    address = models.TextField("آدرس", blank=True)
    file_location = models.CharField(
        "محل نگهداری پرونده", max_length=100, blank=True,
        help_text="مثلاً: قفسه ۳، ردیف ۲",
    )
    notes = models.TextField("توضیحات", blank=True)
    search_name = models.CharField(max_length=200, editable=False, db_index=True, default="")
    created_at = models.DateTimeField("تاریخ ثبت", auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, editable=False,
        on_delete=models.SET_NULL, related_name="+", verbose_name="ثبت‌کننده",
    )

    class Meta:
        verbose_name = "بیمار"
        verbose_name_plural = "بیماران"
        ordering = ["-file_number"]

    def __str__(self):
        return f"{self.file_number or 0} {self.full_name}"

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip()

    @property
    def age(self):
        if not self.birth_date:
            return None
        return jalali_age(self.birth_date, timezone.localdate())

    def save(self, *args, **kwargs):
        self.first_name = normalize_text(self.first_name)
        self.last_name = normalize_text(self.last_name)
        self.search_name = search_key(self.full_name)

        if self.pk is None and self.file_number is None:
            # شماره‌ی پرونده: ترتیبی و خودکار. در صورت هم‌زمانی چند درخواست، دوباره تلاش می‌شود.
            for _ in range(5):
                self.file_number = (Patient.objects.aggregate(m=Max("file_number"))["m"] or 0) + 1
                try:
                    with transaction.atomic():
                        return super().save(*args, **kwargs)
                except IntegrityError:
                    if not Patient.objects.filter(file_number=self.file_number).exists():
                        raise
            raise IntegrityError("تخصیص شماره پرونده ناموفق بود.")
        return super().save(*args, **kwargs)


class Visit(models.Model):
    patient = models.ForeignKey(
        Patient, on_delete=models.CASCADE, related_name="visits", verbose_name="بیمار"
    )
    date = models.DateField("تاریخ مراجعه", default=timezone.localdate, db_index=True)
    notes = models.CharField("توضیحات", max_length=300, blank=True)
    amount = models.PositiveIntegerField("مبلغ (تومان)", null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, editable=False,
        on_delete=models.SET_NULL, related_name="+", verbose_name="ثبت‌کننده",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "مراجعه"
        verbose_name_plural = "مراجعه‌ها"
        ordering = ["-date", "-id"]

    def __str__(self):
        return f"{self.patient_id} @ {self.date}"


def patient_photo_path(instance, filename):
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "jpg"
    return f"patient_photos/{instance.patient_id}/{timezone.now():%Y%m%d%H%M%S%f}.{ext}"


class PatientPhoto(models.Model):
    """عکس دندان/پرونده‌ی بیمار. می‌تواند به یک مراجعه‌ی مشخص وصل باشد یا فقط به خودِ پرونده."""

    patient = models.ForeignKey(
        Patient, on_delete=models.CASCADE, related_name="photos", verbose_name="بیمار"
    )
    visit = models.ForeignKey(
        Visit, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="photos", verbose_name="مراجعه",
    )
    image = models.ImageField("عکس", upload_to=patient_photo_path)
    caption = models.CharField("توضیح", max_length=200, blank=True)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, editable=False,
        on_delete=models.SET_NULL, related_name="+", verbose_name="بارگذاری‌کننده",
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "عکس"
        verbose_name_plural = "عکس‌ها"
        ordering = ["-uploaded_at"]

    def __str__(self):
        return f"عکس {self.patient_id} ({self.uploaded_at:%Y-%m-%d})"


class AuditLog(models.Model):
    LOGIN = "login"
    PATIENT_CREATED = "patient_created"
    PATIENT_UPDATED = "patient_updated"
    PATIENT_DELETED = "patient_deleted"
    VISIT_ADDED = "visit_added"
    VISIT_UPDATED = "visit_updated"
    VISIT_DELETED = "visit_deleted"
    ACTIONS = [
        (LOGIN, "ورود به برنامه"),
        (PATIENT_CREATED, "ثبت بیمار جدید"),
        (PATIENT_UPDATED, "ویرایش پرونده"),
        (PATIENT_DELETED, "حذف بیمار"),
        (VISIT_ADDED, "ثبت مراجعه"),
        (VISIT_UPDATED, "ویرایش مراجعه"),
        (VISIT_DELETED, "حذف مراجعه"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="+", verbose_name="کاربر",
    )
    username = models.CharField("نام کاربری", max_length=150, blank=True)
    action = models.CharField("عملیات", max_length=20, choices=ACTIONS)
    patient = models.ForeignKey(
        Patient, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="+", verbose_name="بیمار",
    )
    patient_label = models.CharField("بیمار", max_length=200, blank=True)
    details = models.TextField("جزئیات", blank=True)
    created_at = models.DateTimeField("زمان", auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = "لاگ تغییرات"
        verbose_name_plural = "لاگ تغییرات"
        ordering = ["-created_at", "-id"]

    def __str__(self):
        return f"{self.username} {self.action}"

    @classmethod
    def record(cls, user, action, patient=None, details="", label=""):
        if not label and patient is not None:
            label = f"{patient.file_number} {patient.full_name}"
        authenticated = getattr(user, "is_authenticated", False)
        return cls.objects.create(
            user=user if authenticated else None,
            username=getattr(user, "username", "") or "",
            action=action,
            patient=patient,
            patient_label=label,
            details=details,
        )
