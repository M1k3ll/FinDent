from django.contrib import admin

from .models import AuditLog, Patient, Visit


@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = ("file_number", "last_name", "first_name", "national_id", "mobile", "file_location")
    search_fields = ("last_name", "first_name", "national_id", "mobile", "file_number")
    readonly_fields = ("file_number", "search_name", "created_at", "updated_at", "created_by")

    def delete_model(self, request, obj):
        AuditLog.record(request.user, AuditLog.PATIENT_DELETED, label=str(obj), details="حذف از بخش مدیریت")
        super().delete_model(request, obj)

    def delete_queryset(self, request, queryset):
        for obj in queryset:
            AuditLog.record(request.user, AuditLog.PATIENT_DELETED, label=str(obj), details="حذف از بخش مدیریت")
        super().delete_queryset(request, queryset)


@admin.register(Visit)
class VisitAdmin(admin.ModelAdmin):
    list_display = ("patient", "date", "notes")
    search_fields = ("patient__last_name", "patient__national_id", "notes")
    autocomplete_fields = ()
    raw_id_fields = ("patient",)


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("created_at", "username", "action", "patient_label")
    list_filter = ("action",)
    search_fields = ("username", "patient_label", "details")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
