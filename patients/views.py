from datetime import date, timedelta
from urllib.parse import urlencode

from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db.models import Max, Q, Sum
from django.http import FileResponse, Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme

from . import credit
from .forms import PatientForm, PatientPhotoForm, VisitForm
from .jalali import format_jalali, jalali_month_bounds, parse_jalali_date, weekday_index
from .models import AuditLog, Patient, PatientPhoto, Visit
from .utils import normalize_text, search_key, to_fa_digits

SEARCH_LIMIT = 30


def access(perm=None):
    """ورود به سیستم الزامی است؛ در صورت نیاز، مجوز مشخصی هم بررسی می‌شود."""

    def decorator(view):
        wrapped = permission_required(perm, raise_exception=True)(view) if perm else view
        return login_required(wrapped)

    return decorator


def _fmt(value):
    if value is None or value == "":
        return "—"
    if isinstance(value, date):
        return format_jalali(value)
    return str(value)


def _changes(form):
    """فهرست تغییرات واقعی فرم (قدیم و جدید) برای ثبت در لاگ."""
    out = []
    for name in form.changed_data:
        old = form.initial.get(name)
        new = form.cleaned_data.get(name)
        if _fmt(old) != _fmt(new):
            out.append(f"«{form.fields[name].label}» از «{_fmt(old)}» به «{_fmt(new)}»")
    return out


def _safe_next(request, fallback):
    nxt = request.POST.get("next") or request.GET.get("next")
    if nxt and url_has_allowed_host_and_scheme(
        nxt, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    ):
        return nxt
    return fallback


# ---------------------------------------------------------------- خانه


def about(request):
    """درباره ما / ارتباط با ما — قابل دیدن حتی قبل از ورود (لینک پایین صفحه‌ی ورود هم هست)."""
    return render(request, "patients/about.html", {"about_text": credit.ABOUT_TEXT})


@access()
def home(request):
    can_settings = request.user.is_staff or request.user.has_perm("patients.view_auditlog")
    return render(request, "home.html", {"can_settings": can_settings})


# ---------------------------------------------------------------- جستجو


def find_patients(raw_query, limit=SEARCH_LIMIT):
    """جستجو با کدملی، موبایل، شماره پرونده یا نام. خروجی: لیست بیماران."""
    query = normalize_text(raw_query)
    if not query:
        return []

    base = Patient.objects.annotate(last_visit=Max("visits__date"))
    compact = query.replace(" ", "").replace("-", "")

    if compact.isdigit():
        number = int(compact)
        cond = Q(national_id__startswith=compact)
        if len(compact) >= 4:
            cond |= Q(mobile__contains=compact)
        if len(compact) <= 9:
            cond |= Q(file_number=number)
        results = list(base.filter(cond).order_by("last_name", "first_name")[:limit])
        # اگر شماره‌ی پرونده دقیقاً برابر بود، اول نمایش داده شود
        results.sort(key=lambda p: p.file_number != number)
        return results

    tokens = [search_key(t) for t in query.split(" ")]
    tokens = [t for t in tokens if t]
    if not tokens:
        return []
    cond = Q()
    for token in tokens:
        cond &= Q(search_name__contains=token)
    return list(base.filter(cond).order_by("last_name", "first_name")[:limit])


@access("patients.view_patient")
def search(request):
    q = request.GET.get("q", "").strip()
    results = find_patients(q)
    context = {
        "q": q,
        "results": results,
        "limit": SEARCH_LIMIT,
        "next_url": reverse("search") + "?" + urlencode({"q": q}),
    }
    if request.GET.get("partial"):
        html = render_to_string("patients/_results.html", context, request=request)
        return HttpResponse(html)
    return render(request, "patients/search.html", context)


# ---------------------------------------------------------------- بیمار


@access("patients.view_patient")
def patient_detail(request, pk):
    patient = get_object_or_404(Patient, pk=pk)
    visits = list(patient.visits.all())
    today = timezone.localdate()
    context = {
        "patient": patient,
        "visits": visits,
        "visited_today": any(v.date == today for v in visits),
        "form": VisitForm(),
    }
    return render(request, "patients/detail.html", context)


@access("patients.add_patient")
def patient_create(request):
    form = PatientForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        patient = form.save(commit=False)
        patient.created_by = request.user
        patient.save()
        AuditLog.record(request.user, AuditLog.PATIENT_CREATED, patient)
        messages.success(
            request,
            f"پرونده جدید با شماره {to_fa_digits(f'{patient.file_number}')} ثبت شد. "
            "این شماره را روی پوشه بنویسید.",
        )
        same_mobile = Patient.objects.filter(mobile=patient.mobile).exclude(pk=patient.pk)
        if same_mobile.exists():
            names = "، ".join(p.full_name for p in same_mobile[:3])
            messages.warning(request, f"این شماره موبایل برای بیمار دیگری هم ثبت شده است: {names}")
        return redirect("patient_detail", pk=patient.pk)
    return render(request, "patients/form.html", {"form": form, "patient": None})


@access("patients.change_patient")
def patient_edit(request, pk):
    patient = get_object_or_404(Patient, pk=pk)
    form = PatientForm(request.POST or None, instance=patient)
    if request.method == "POST" and form.is_valid():
        changes = _changes(form)
        if not changes:
            messages.info(request, "تغییری وجود نداشت.")
            return redirect("patient_detail", pk=patient.pk)
        form.save()
        AuditLog.record(request.user, AuditLog.PATIENT_UPDATED, patient, "\n".join(changes))
        messages.success(request, "تغییرات ذخیره شد.")
        return redirect("patient_detail", pk=patient.pk)
    return render(request, "patients/form.html", {"form": form, "patient": patient})


# ---------------------------------------------------------------- مراجعه


@access("patients.add_visit")
def visit_add(request, pk):
    patient = get_object_or_404(Patient, pk=pk)
    today = timezone.localdate()
    detail_url = reverse("patient_detail", args=[patient.pk])
    next_url = request.POST.get("next") or request.GET.get("next") or ""

    if request.method == "POST":
        form = VisitForm(request.POST)
        photo_file = request.FILES.get("image")
        if form.is_valid():
            visit_date = form.cleaned_data["date"] or today
            duplicate = patient.visits.filter(date=visit_date).exists()
            if duplicate and not request.POST.get("force"):
                return render(
                    request,
                    "patients/visit_confirm.html",
                    {"patient": patient, "form": form, "visit_date": visit_date,
                     "duplicate": True, "next": next_url},
                )
            visit = Visit.objects.create(
                patient=patient,
                date=visit_date,
                notes=form.cleaned_data["notes"],
                amount=form.cleaned_data.get("amount"),
                created_by=request.user,
            )
            details = format_jalali(visit.date)
            if visit.notes:
                details += f"\n{visit.notes}"
            AuditLog.record(request.user, AuditLog.VISIT_ADDED, patient, details)

            if photo_file:
                photo_form = PatientPhotoForm(request.POST, request.FILES)
                if photo_form.is_valid():
                    PatientPhoto.objects.create(
                        patient=patient, visit=visit,
                        image=photo_form.cleaned_data["image"],
                        caption=photo_form.cleaned_data.get("caption", ""),
                        uploaded_by=request.user,
                    )
                else:
                    errs = "؛ ".join(e for field_errs in photo_form.errors.values() for e in field_errs)
                    messages.warning(request, f"مراجعه ثبت شد ولی عکس ذخیره نشد: {errs}")

            messages.success(
                request, f"مراجعه {format_jalali(visit.date)} برای {patient.full_name} ثبت شد."
            )
            return redirect(_safe_next(request, detail_url))
        # فرم نامعتبر (مثلاً تاریخ اشتباه): به صفحه‌ی تأیید با خطا برمی‌گردیم
        return render(
            request,
            "patients/visit_confirm.html",
            {"patient": patient, "form": form, "visit_date": today,
             "duplicate": False, "next": next_url},
        )

    context = {
        "patient": patient,
        "form": VisitForm(),
        "visit_date": today,
        "duplicate": patient.visits.filter(date=today).exists(),
        "next": next_url,
    }
    return render(request, "patients/visit_confirm.html", context)


@access("patients.change_visit")
def visit_edit(request, pk):
    visit = get_object_or_404(Visit.objects.select_related("patient"), pk=pk)
    form = VisitForm(request.POST or None, instance=visit, require_date=True)
    if request.method == "POST" and form.is_valid():
        changes = _changes(form)
        if changes:
            form.save()
            AuditLog.record(request.user, AuditLog.VISIT_UPDATED, visit.patient, "\n".join(changes))
            messages.success(request, "مراجعه ویرایش شد.")
        else:
            messages.info(request, "تغییری وجود نداشت.")
        return redirect("patient_detail", pk=visit.patient_id)
    return render(request, "patients/visit_edit.html", {"form": form, "visit": visit})


@access("patients.delete_visit")
def visit_delete(request, pk):
    visit = get_object_or_404(Visit.objects.select_related("patient"), pk=pk)
    patient = visit.patient
    if request.method == "POST":
        details = format_jalali(visit.date)
        if visit.notes:
            details += f"\n{visit.notes}"
        visit.delete()
        AuditLog.record(request.user, AuditLog.VISIT_DELETED, patient, details)
        messages.success(request, "مراجعه حذف شد.")
        return redirect("patient_detail", pk=patient.pk)
    return render(request, "patients/visit_delete.html", {"visit": visit})


# ---------------------------------------------------------------- عکس‌های بیمار


@access("patients.add_patientphoto")
def patient_photo_add(request, pk):
    patient = get_object_or_404(Patient, pk=pk)
    next_url = _safe_next(request, reverse("patient_detail", args=[patient.pk]))
    if request.method == "POST":
        form = PatientPhotoForm(request.POST, request.FILES)
        if form.is_valid():
            PatientPhoto.objects.create(
                patient=patient,
                image=form.cleaned_data["image"],
                caption=form.cleaned_data.get("caption", ""),
                uploaded_by=request.user,
            )
            messages.success(request, "عکس اضافه شد.")
        else:
            errs = "؛ ".join(e for field_errs in form.errors.values() for e in field_errs)
            messages.error(request, f"عکس ذخیره نشد: {errs}")
    return redirect(next_url)


@access("patients.view_patientphoto")
def patient_photo_file(request, pk):
    """فایل عکس؛ فقط از این آدرس قابل دیدن است، نه با لینک مستقیم بدون ورود."""
    photo = get_object_or_404(PatientPhoto, pk=pk)
    return FileResponse(photo.image.open("rb"))


@access("patients.delete_patientphoto")
def patient_photo_delete(request, pk):
    photo = get_object_or_404(PatientPhoto.objects.select_related("patient"), pk=pk)
    patient = photo.patient
    if request.method == "POST":
        photo.image.delete(save=False)
        photo.delete()
        messages.success(request, "عکس حذف شد.")
        return redirect("patient_detail", pk=patient.pk)
    return render(request, "patients/photo_delete.html", {"photo": photo})


# ---------------------------------------------------------------- گزارش مراجعین (هفته/ماه/کل)


@access("patients.view_visit")
def visits_report(request):
    period = request.GET.get("period", "week")
    if period not in ("week", "month", "all"):
        period = "week"
    today = timezone.localdate()
    context = {"period": period}

    if period in ("week", "month"):
        try:
            offset = int(request.GET.get("offset", 0))
        except ValueError:
            offset = 0
        offset = max(-1200, min(0, offset))

        if period == "week":
            start = today - timedelta(days=weekday_index(today)) + timedelta(weeks=offset)
            end = start + timedelta(days=6)
            title_current = "این هفته"
        else:
            start, end, _, _ = jalali_month_bounds(today, offset)
            title_current = "این ماه"

        visits = list(
            Visit.objects.filter(date__range=(start, end))
            .select_related("patient")
            .order_by("date", "id")
        )
        by_date = {}
        for v in visits:
            by_date.setdefault(v.date, []).append(v)
        days = [{"date": d, "visits": by_date[d]} for d in sorted(by_date)]
        total_amount = sum(v.amount or 0 for v in visits)

        context.update({
            "days": days,
            "total": len(visits),
            "patients_count": len({v.patient_id for v in visits}),
            "total_amount": total_amount,
            "start": start,
            "end": end,
            "offset": offset,
            "prev_offset": offset - 1,
            "next_offset": offset + 1,
            "is_current": offset == 0,
            "title_current": title_current,
        })
        return render(request, "patients/visits_report.html", context)

    # period == "all"
    date_from = date_to = None
    error = None
    from_raw = request.GET.get("from", "").strip()
    to_raw = request.GET.get("to", "").strip()
    try:
        if from_raw:
            date_from = parse_jalali_date(from_raw)
        if to_raw:
            date_to = parse_jalali_date(to_raw)
    except ValueError:
        error = "تاریخ وارد شده معتبر نیست. به شکل 1405/06/29 وارد کنید."

    qs = Visit.objects.select_related("patient").order_by("-date", "-id")
    if not error:
        if date_from:
            qs = qs.filter(date__gte=date_from)
        if date_to:
            qs = qs.filter(date__lte=date_to)

    total_amount = qs.aggregate(s=Sum("amount"))["s"] or 0
    total_count = qs.count()
    page = Paginator(qs, 100).get_page(request.GET.get("page"))

    context.update({
        "page": page,
        "from_raw": from_raw,
        "to_raw": to_raw,
        "error": error,
        "total": total_count,
        "total_amount": total_amount,
    })
    return render(request, "patients/visits_report.html", context)


# ---------------------------------------------------------------- تنظیمات و لاگ


def _can_see_settings(user):
    return user.is_staff or user.has_perm("patients.view_auditlog")


@access()
def settings_page(request):
    if not _can_see_settings(request.user):
        raise PermissionDenied
    return render(request, "patients/settings.html")


@access()
def audit_log(request):
    if not request.user.has_perm("patients.view_auditlog"):
        raise PermissionDenied
    only_changes = request.GET.get("only") == "changes"
    logs = AuditLog.objects.all()
    if only_changes:
        logs = logs.exclude(action=AuditLog.LOGIN)
    page = Paginator(logs, 50).get_page(request.GET.get("page"))
    return render(request, "patients/audit_log.html", {"page": page, "only_changes": only_changes})
