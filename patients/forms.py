import re
from datetime import date

from django import forms
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils import timezone

from .jalali import format_jalali, parse_jalali_date
from .models import Patient, Visit
from .utils import digits_only, is_valid_national_id, normalize_text, to_fa_digits


class JalaliDateField(forms.Field):
    """فیلد تاریخ شمسی (مثل 1405/06/29) که در دیتابیس به میلادی ذخیره می‌شود."""

    default_error_messages = {
        "invalid": "تاریخ را به شکل 1405/06/29 وارد کنید و درست بودن روز و ماه را بررسی کنید.",
    }

    def __init__(self, *args, **kwargs):
        kwargs.setdefault(
            "widget",
            forms.TextInput(
                attrs={
                    "class": "num",
                    "dir": "ltr",
                    "placeholder": "1405/06/29",
                    "inputmode": "numeric",
                    "autocomplete": "off",
                }
            ),
        )
        super().__init__(*args, **kwargs)

    def to_python(self, value):
        if value in self.empty_values:
            return None
        try:
            return parse_jalali_date(str(value))
        except ValueError:
            raise ValidationError(self.error_messages["invalid"], code="invalid")

    def prepare_value(self, value):
        if isinstance(value, date):
            return format_jalali(value)
        return value


class PatientForm(forms.ModelForm):
    birth_date = JalaliDateField(
        label="تاریخ تولد (شمسی)", required=False, help_text="مثلاً 1370/05/12"
    )

    class Meta:
        model = Patient
        fields = [
            "first_name", "last_name", "national_id", "mobile",
            "birth_date", "address", "file_location", "notes",
        ]
        widgets = {
            "national_id": forms.TextInput(
                attrs={"class": "num", "dir": "ltr", "inputmode": "numeric", "maxlength": "10", "autocomplete": "off"}
            ),
            "mobile": forms.TextInput(
                attrs={"class": "num", "dir": "ltr", "inputmode": "numeric", "maxlength": "11", "autocomplete": "off"}
            ),
            "address": forms.Textarea(attrs={"rows": 2}),
            "notes": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.label_suffix = ""

    def clean_first_name(self):
        return normalize_text(self.cleaned_data["first_name"])

    def clean_last_name(self):
        return normalize_text(self.cleaned_data["last_name"])

    # def clean_national_id(self):
    #     value = digits_only(self.cleaned_data["national_id"])
    #     if len(value) != 10:
    #         raise ValidationError("کدملی باید ۱۰ رقم باشد.")
    #     if settings.FINDENT_STRICT_NATIONAL_ID and not is_valid_national_id(value):
    #         raise ValidationError("این کدملی معتبر نیست. ارقام را دوباره بررسی کنید.")
    #     others = Patient.objects.filter(national_id=value)
    #     if self.instance.pk:
    #         others = others.exclude(pk=self.instance.pk)
    #     other = others.first()
    #     if other:
    #         raise ValidationError(
    #             f"این کدملی قبلاً برای «{other.full_name}» با شماره پرونده "
    #             f"{to_fa_digits(f'{other.file_number:05d}')} ثبت شده است."
    #         )
    #     return value

    def clean_national_id(self):
        value = digits_only(self.cleaned_data["national_id"])
        if not value:
            raise ValidationError("کدملی باید شامل رقم باشد.")

        # اشکال طول یا فرمت خطای قطعی نیست، فقط هشدار است (بیمار خارجی یا بدون کدملی).
        # اگر کاربر دکمه‌ی «بله، با همین کدملی ثبت شود» را بزند، خود همین کد را
        # در confirm_national_id می‌فرستد و ثبت انجام می‌شود.
        problem = None
        if len(value) != 10:
            problem = (
                f"طول کدملی {to_fa_digits(len(value))} رقم است، در حالی که کدملی ایرانی "
                "باید ۱۰ رقم باشد."
            )
        elif not is_valid_national_id(value):
            problem = (
                "فرمت کدملی درست نیست؛ ۱۰ رقم است ولی با الگوریتم کدملی ایران نمی‌خواند "
                "(ممکن است اشتباه تایپ شده باشد)."
            )

        unchanged = bool(self.instance.pk) and self.instance.national_id == value
        confirmed = digits_only(self.data.get("confirm_national_id", "")) == value
        if problem and not unchanged and not confirmed:
            self.national_id_warning = True
            self.national_id_problem = problem
            self.national_id_confirm_value = value
            raise ValidationError(problem)

        others = Patient.objects.filter(national_id=value)
        if self.instance.pk:
            others = others.exclude(pk=self.instance.pk)
        other = others.first()
        if other:
            raise ValidationError(
                f"این کدملی قبلاً برای «{other.full_name}» با شماره پرونده "
                f"{to_fa_digits(f'{other.file_number:05d}')} ثبت شده است."
            )
        return value
    

    def clean_mobile(self):
        value = digits_only(self.cleaned_data["mobile"])
        if len(value) == 12 and value.startswith("98"):
            value = "0" + value[2:]
        elif len(value) == 10 and value.startswith("9"):
            value = "0" + value
        if not re.fullmatch(r"09\d{9}", value):
            raise ValidationError("شماره موبایل باید به شکل 09123456789 باشد.")
        return value

    def clean_birth_date(self):
        value = self.cleaned_data.get("birth_date")
        if value and value > timezone.localdate():
            raise ValidationError("تاریخ تولد نمی‌تواند در آینده باشد.")
        return value


class VisitForm(forms.ModelForm):
    date = JalaliDateField(label="تاریخ مراجعه (شمسی)", required=False)

    class Meta:
        model = Visit
        fields = ["date", "notes"]
        widgets = {
            "notes": forms.TextInput(
                attrs={"placeholder": "توضیحات (اختیاری)", "maxlength": "300"}
            ),
        }

    def __init__(self, *args, require_date=False, **kwargs):
        super().__init__(*args, **kwargs)
        self.label_suffix = ""
        self.fields["date"].required = require_date
        self.national_id_warning = False
        self.national_id_problem = ""
        self.national_id_confirm_value = ""

    def clean_date(self):
        value = self.cleaned_data.get("date")
        if value and value > timezone.localdate():
            raise ValidationError("تاریخ مراجعه نمی‌تواند در آینده باشد.")
        return value
