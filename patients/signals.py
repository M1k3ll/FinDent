from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver

from .models import AuditLog


@receiver(user_logged_in)
def log_login(sender, request, user, **kwargs):
    AuditLog.record(user, AuditLog.LOGIN)
