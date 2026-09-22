from datetime import datetime

from django import template
from django.utils import timezone

from ..jalali import format_jalali, format_jalali_long
from ..utils import to_fa_digits

register = template.Library()


@register.filter
def fa_digits(value):
    """ارقام را فارسی می‌کند."""
    if value is None:
        return ""
    return to_fa_digits(value)


@register.filter
def file_no(value):
    """شماره پرونده بدون صفر پیشوند و با ارقام فارسی: ۱۲۳"""
    try:
        return to_fa_digits(f"{int(value)}")
    except (TypeError, ValueError):
        return ""


def _as_date(value):
    if isinstance(value, datetime):
        return timezone.localtime(value).date()
    return value


@register.filter
def jdate(value):
    """تاریخ شمسی: ۱۴۰۵/۰۶/۲۹"""
    if not value:
        return "—"
    return to_fa_digits(format_jalali(_as_date(value)))


@register.filter
def jlong(value):
    """تاریخ شمسی بلند: شنبه ۲۹ شهریور ۱۴۰۵"""
    if not value:
        return "—"
    return to_fa_digits(format_jalali_long(_as_date(value)))


@register.filter
def jdatetime(value):
    if not value:
        return "—"
    local = timezone.localtime(value)
    return to_fa_digits(f"{format_jalali(local.date())} {local:%H:%M}")
