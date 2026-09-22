from datetime import date, timedelta
from urllib.parse import urlencode

from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db.models import Max, Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme

from .forms import PatientForm, VisitForm
from .jalali import format_jalali, weekday_index
from .models import AuditLog, Patient, Visit
from .utils import normalize_text, search_key, to_fa_digits
from . import credit

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
        """درباره ما / ارتباط با ما — قابل دیدن حتی قبل از ورود."""
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
                created_by=request.user,
            )
            details = format_jalali(visit.date)
            if visit.notes:
                details += f"\n{visit.notes}"
            AuditLog.record(request.user, AuditLog.VISIT_ADDED, patient, details)
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


# ---------------------------------------------------------------- مراجعه‌های هفته


@access("patients.view_visit")
def week_visits(request):
    try:
        offset = max(-520, min(0, int(request.GET.get("week", 0))))
    except ValueError:
        offset = 0
    today = timezone.localdate()
    # هفته‌ی ایرانی از شنبه شروع می‌شود و جمعه تمام می‌شود
    start = today - timedelta(days=weekday_index(today)) + timedelta(weeks=offset)
    end = start + timedelta(days=6)

    visits = list(
        Visit.objects.filter(date__range=(start, end))
        .select_related("patient")
        .order_by("date", "id")
    )
    by_date = {}
    for v in visits:
        by_date.setdefault(v.date, []).append(v)
    days = [{"date": d, "visits": by_date[d]} for d in sorted(by_date)]

    context = {
        "days": days,
        "total": len(visits),
        "patients_count": len({v.patient_id for v in visits}),
        "start": start,
        "end": end,
        "offset": offset,
        "prev_offset": offset - 1,
        "next_offset": offset + 1,
        "is_current": offset == 0,
    }
    return render(request, "patients/week.html", context)


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
