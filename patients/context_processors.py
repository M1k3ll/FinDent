from . import credit


def site_credit(request):
    """اطلاعات «درباره ما» را در context همه‌ی صفحات قرار می‌دهد (پایین‌تر در base.html)."""
    return {
        "site_developer_name": credit.DEVELOPER_NAME,
        "site_developer_phone": credit.DEVELOPER_PHONE,
        "site_developer_email": credit.DEVELOPER_EMAIL,
    }
