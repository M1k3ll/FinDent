# """تبدیل تاریخ میلادی و شمسی (بدون وابستگی خارجی)."""
# import re
# from datetime import date

# from .utils import to_en_digits

# JALALI_MONTHS = [
#     "فروردین", "اردیبهشت", "خرداد", "تیر", "مرداد", "شهریور",
#     "مهر", "آبان", "آذر", "دی", "بهمن", "اسفند",
# ]
# # شنبه = 0 ... جمعه = 6
# WEEKDAYS = ["شنبه", "یکشنبه", "دوشنبه", "سه‌شنبه", "چهارشنبه", "پنجشنبه", "جمعه"]


# def weekday_index(d):
#     """شماره‌ی روز هفته در تقویم ایران (شنبه = ۰)."""
#     return (d.weekday() + 2) % 7


# def gregorian_to_jalali(gy, gm, gd):
#     g_d_m = [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334]
#     gy2 = gy + 1 if gm > 2 else gy
#     days = (
#         355666 + (365 * gy) + ((gy2 + 3) // 4) - ((gy2 + 99) // 100)
#         + ((gy2 + 399) // 400) + gd + g_d_m[gm - 1]
#     )
#     jy = -1595 + (33 * (days // 12053))
#     days %= 12053
#     jy += 4 * (days // 1461)
#     days %= 1461
#     if days > 365:
#         jy += (days - 1) // 365
#         days = (days - 1) % 365
#     if days < 186:
#         jm = 1 + days // 31
#         jd = 1 + days % 31
#     else:
#         jm = 7 + (days - 186) // 30
#         jd = 1 + (days - 186) % 30
#     return jy, jm, jd


# def jalali_to_gregorian(jy, jm, jd):
#     jy += 1595
#     days = -355668 + (365 * jy) + ((jy // 33) * 8) + (((jy % 33) + 3) // 4) + jd
#     if jm < 7:
#         days += (jm - 1) * 31
#     else:
#         days += ((jm - 7) * 30) + 186
#     gy = 400 * (days // 146097)
#     days %= 146097
#     if days > 36524:
#         days -= 1
#         gy += 100 * (days // 36524)
#         days %= 36524
#         if days >= 365:
#             days += 1
#     gy += 4 * (days // 1461)
#     days %= 1461
#     if days > 365:
#         gy += (days - 1) // 365
#         days = (days - 1) % 365
#     gd = days + 1
#     leap = (gy % 4 == 0 and gy % 100 != 0) or gy % 400 == 0
#     month_days = [0, 31, 29 if leap else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
#     gm = 0
#     while gm < 13 and gd > month_days[gm]:
#         gd -= month_days[gm]
#         gm += 1
#     return gy, gm, gd


# def to_jalali(d):
#     return gregorian_to_jalali(d.year, d.month, d.day)


# def format_jalali(d):
#     jy, jm, jd = to_jalali(d)
#     return f"{jy:04d}/{jm:02d}/{jd:02d}"


# def format_jalali_long(d):
#     jy, jm, jd = to_jalali(d)
#     return f"{WEEKDAYS[weekday_index(d)]} {jd} {JALALI_MONTHS[jm - 1]} {jy}"


# _DATE_RE = re.compile(r"^(\d{4})/(\d{1,2})/(\d{1,2})$")


# def parse_jalali_date(text):
#     """رشته‌ی شمسی مثل 1405/06/29 (یا 14050629) را به date میلادی تبدیل می‌کند."""
#     text = to_en_digits(text).strip()
#     text = re.sub(r"[-.\\]", "/", text)
#     if re.fullmatch(r"\d{8}", text):
#         text = f"{text[:4]}/{text[4:6]}/{text[6:]}"
#     m = _DATE_RE.match(text)
#     if not m:
#         raise ValueError("bad format")
#     jy, jm, jd = (int(x) for x in m.groups())
#     if not (1200 <= jy <= 1600 and 1 <= jm <= 12 and 1 <= jd <= 31):
#         raise ValueError("out of range")
#     try:
#         gy, gm, gd = jalali_to_gregorian(jy, jm, jd)
#         result = date(gy, gm, gd)
#     except (ValueError, IndexError):
#         raise ValueError("invalid date")
#     # روز نامعتبر (مثل ۳۱ شهریور... یا ۳۰ اسفند در سال کبیسه‌نشده) با رفت‌وبرگشت شناسایی می‌شود
#     if to_jalali(result) != (jy, jm, jd):
#         raise ValueError("invalid day")
#     return result


# def jalali_age(birth, today):
#     by, bm, bd = to_jalali(birth)
#     ty, tm, td = to_jalali(today)
#     age = ty - by
#     if (tm, td) < (bm, bd):
#         age -= 1
#     return age


"""تبدیل تاریخ میلادی و شمسی (بدون وابستگی خارجی)."""
import re
from datetime import date, timedelta

from .utils import to_en_digits

JALALI_MONTHS = [
    "فروردین", "اردیبهشت", "خرداد", "تیر", "مرداد", "شهریور",
    "مهر", "آبان", "آذر", "دی", "بهمن", "اسفند",
]
# شنبه = 0 ... جمعه = 6
WEEKDAYS = ["شنبه", "یکشنبه", "دوشنبه", "سه‌شنبه", "چهارشنبه", "پنجشنبه", "جمعه"]


def weekday_index(d):
    """شماره‌ی روز هفته در تقویم ایران (شنبه = ۰)."""
    return (d.weekday() + 2) % 7


def gregorian_to_jalali(gy, gm, gd):
    g_d_m = [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334]
    gy2 = gy + 1 if gm > 2 else gy
    days = (
        355666 + (365 * gy) + ((gy2 + 3) // 4) - ((gy2 + 99) // 100)
        + ((gy2 + 399) // 400) + gd + g_d_m[gm - 1]
    )
    jy = -1595 + (33 * (days // 12053))
    days %= 12053
    jy += 4 * (days // 1461)
    days %= 1461
    if days > 365:
        jy += (days - 1) // 365
        days = (days - 1) % 365
    if days < 186:
        jm = 1 + days // 31
        jd = 1 + days % 31
    else:
        jm = 7 + (days - 186) // 30
        jd = 1 + (days - 186) % 30
    return jy, jm, jd


def jalali_to_gregorian(jy, jm, jd):
    jy += 1595
    days = -355668 + (365 * jy) + ((jy // 33) * 8) + (((jy % 33) + 3) // 4) + jd
    if jm < 7:
        days += (jm - 1) * 31
    else:
        days += ((jm - 7) * 30) + 186
    gy = 400 * (days // 146097)
    days %= 146097
    if days > 36524:
        days -= 1
        gy += 100 * (days // 36524)
        days %= 36524
        if days >= 365:
            days += 1
    gy += 4 * (days // 1461)
    days %= 1461
    if days > 365:
        gy += (days - 1) // 365
        days = (days - 1) % 365
    gd = days + 1
    leap = (gy % 4 == 0 and gy % 100 != 0) or gy % 400 == 0
    month_days = [0, 31, 29 if leap else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    gm = 0
    while gm < 13 and gd > month_days[gm]:
        gd -= month_days[gm]
        gm += 1
    return gy, gm, gd


def to_jalali(d):
    return gregorian_to_jalali(d.year, d.month, d.day)


def format_jalali(d):
    jy, jm, jd = to_jalali(d)
    return f"{jy:04d}/{jm:02d}/{jd:02d}"


def format_jalali_long(d):
    jy, jm, jd = to_jalali(d)
    return f"{WEEKDAYS[weekday_index(d)]} {jd} {JALALI_MONTHS[jm - 1]} {jy}"


_DATE_RE = re.compile(r"^(\d{4})/(\d{1,2})/(\d{1,2})$")


def parse_jalali_date(text):
    """رشته‌ی شمسی مثل 1405/06/29 (یا 14050629) را به date میلادی تبدیل می‌کند."""
    text = to_en_digits(text).strip()
    text = re.sub(r"[-.\\]", "/", text)
    if re.fullmatch(r"\d{8}", text):
        text = f"{text[:4]}/{text[4:6]}/{text[6:]}"
    m = _DATE_RE.match(text)
    if not m:
        raise ValueError("bad format")
    jy, jm, jd = (int(x) for x in m.groups())
    if not (1200 <= jy <= 1600 and 1 <= jm <= 12 and 1 <= jd <= 31):
        raise ValueError("out of range")
    try:
        gy, gm, gd = jalali_to_gregorian(jy, jm, jd)
        result = date(gy, gm, gd)
    except (ValueError, IndexError):
        raise ValueError("invalid date")
    # روز نامعتبر (مثل ۳۱ شهریور... یا ۳۰ اسفند در سال کبیسه‌نشده) با رفت‌وبرگشت شناسایی می‌شود
    if to_jalali(result) != (jy, jm, jd):
        raise ValueError("invalid day")
    return result


def jalali_age(birth, today):
    by, bm, bd = to_jalali(birth)
    ty, tm, td = to_jalali(today)
    age = ty - by
    if (tm, td) < (bm, bd):
        age -= 1
    return age


def jalali_month_bounds(today, offset=0):
    """بازه‌ی میلادیِ یک ماه شمسی را برمی‌گرداند (offset: چند ماه قبل/بعد).
    خروجی: (start, end, jy, jm) — start و end از نوع date میلادی هستند."""
    jy, jm, _ = to_jalali(today)
    total = (jy * 12 + (jm - 1)) + offset
    jy2, jm2 = divmod(total, 12)
    jm2 += 1
    start = date(*jalali_to_gregorian(jy2, jm2, 1))
    ny, nm = (jy2 + 1, 1) if jm2 == 12 else (jy2, jm2 + 1)
    end = date(*jalali_to_gregorian(ny, nm, 1)) - timedelta(days=1)
    return start, end, jy2, jm2
