"""نرمال‌سازی متن فارسی، ارقام و اعتبارسنجی کدملی."""
import re

_TO_EN = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")
_TO_FA = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")
# «ي» و «ك» عربی و «ى» را به فارسی تبدیل می‌کند
_CHARS = str.maketrans({"ي": "ی", "ك": "ک", "ى": "ی"})
_MARKS = re.compile("[\u064B-\u065F\u0670\u0640]")  # اعراب و کشیده


def to_en_digits(value):
    return str(value).translate(_TO_EN)


def to_fa_digits(value):
    return str(value).translate(_TO_FA)


def normalize_text(value):
    """یکسان‌سازی حروف و ارقام و فاصله‌ها برای ذخیره و جستجو."""
    value = to_en_digits(value or "").translate(_CHARS)
    value = _MARKS.sub("", value)
    return re.sub(r"\s+", " ", value).strip()


def search_key(value):
    """کلید جستجو: بدون فاصله و نیم‌فاصله، تا «علی اکبر» و «علی‌اکبر» یکی حساب شوند."""
    return normalize_text(value).replace("\u200c", "").replace(" ", "")


def digits_only(value):
    return re.sub(r"\D", "", to_en_digits(value or ""))


def is_valid_national_id(code):
    if not re.fullmatch(r"\d{10}", code) or len(set(code)) == 1:
        return False
    total = sum(int(code[i]) * (10 - i) for i in range(9))
    r = total % 11
    check = int(code[9])
    return check == r if r < 2 else check == 11 - r
