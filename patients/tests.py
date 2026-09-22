from datetime import date, timedelta

from django.contrib.auth.models import Group, User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import AuditLog, Patient, Visit
from .utils import is_valid_national_id


def make_nid(base9):
    total = sum(int(base9[i]) * (10 - i) for i in range(9))
    r = total % 11
    return base9 + str(r if r < 2 else 11 - r)


def make_patient(n=1, **kw):
    data = dict(
        first_name="علی", last_name="رضایی",
        national_id=make_nid(f"{n:09d}"), mobile=f"0912000{n:04d}",
    )
    data.update(kw)
    return Patient.objects.create(**data)


def login_as(client, group_name):
    user = User.objects.create_user(f"u_{group_name}", password="pw-12345678")
    user.groups.add(Group.objects.get(name=group_name))
    client.force_login(user)
    return user


class PatientModelTests(TestCase):
    def test_file_numbers_are_sequential_and_stable(self):
        p1, p2 = make_patient(1), make_patient(2)
        self.assertEqual((p1.file_number, p2.file_number), (1, 2))
        p1.mobile = "09129999999"
        p1.save()
        p1.refresh_from_db()
        self.assertEqual(p1.file_number, 1)

    def test_names_are_normalized(self):
        p = make_patient(1, first_name="علي", last_name="كريمي")
        self.assertEqual(p.full_name, "علی کریمی")

    def test_national_id_validator(self):
        self.assertTrue(is_valid_national_id(make_nid("049937089")))
        self.assertFalse(is_valid_national_id("1111111111"))


class AccessTests(TestCase):
    def test_anonymous_is_redirected_to_login(self):
        resp = self.client.get(reverse("search"))
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/login/", resp["Location"])

    def test_secretary_cannot_delete_visit_but_doctor_can(self):
        patient = make_patient(1)
        visit = Visit.objects.create(patient=patient, date=timezone.localdate())
        login_as(self.client, "منشی")
        resp = self.client.post(reverse("visit_delete", args=[visit.pk]))
        self.assertEqual(resp.status_code, 403)
        self.assertTrue(Visit.objects.filter(pk=visit.pk).exists())

        self.client.logout()
        login_as(self.client, "دکتر")
        resp = self.client.post(reverse("visit_delete", args=[visit.pk]))
        self.assertEqual(resp.status_code, 302)
        self.assertFalse(Visit.objects.filter(pk=visit.pk).exists())


class SearchTests(TestCase):
    def setUp(self):
        login_as(self.client, "منشی")
        self.patient = make_patient(7, first_name="مریم", last_name="احمدی")

    def found(self, q):
        resp = self.client.get(reverse("search"), {"q": q})
        self.assertEqual(resp.status_code, 200)
        return self.patient in resp.context["results"]

    def test_search_by_all_keys(self):
        self.assertTrue(self.found(self.patient.national_id))
        self.assertTrue(self.found("۰" + self.patient.national_id[1:]))  # Persian digits
        self.assertTrue(self.found(self.patient.mobile))
        self.assertTrue(self.found(self.patient.mobile[-5:]))
        self.assertTrue(self.found(str(self.patient.file_number)))
        self.assertTrue(self.found("احمدی"))
        self.assertTrue(self.found("مریم احمدی"))

    def test_arabic_letters_match(self):
        Patient.objects.all().delete()
        self.patient = make_patient(8, first_name="علی", last_name="کریمی")
        self.assertTrue(self.found("كريمي"))

    def test_no_match(self):
        self.assertFalse(self.found("ناموجود"))

    def test_partial_response(self):
        resp = self.client.get(reverse("search"), {"q": "احمدی", "partial": "1"})
        self.assertContains(resp, "احمدی")
        self.assertNotContains(resp, "<html")


class PatientFormTests(TestCase):
    def setUp(self):
        self.user = login_as(self.client, "منشی")
        self.data = {
            "first_name": "سارا", "last_name": "احمدی",
            "national_id": make_nid("123456789"), "mobile": "09121234567",
            "birth_date": "1370/05/12", "address": "", "file_location": "قفسه ۳", "notes": "",
        }

    def test_create_patient(self):
        resp = self.client.post(reverse("patient_create"), self.data)
        self.assertEqual(resp.status_code, 302)
        patient = Patient.objects.get()
        self.assertEqual(patient.file_number, 1)
        self.assertEqual(patient.birth_date, date(1991, 8, 3))
        self.assertEqual(patient.created_by, self.user)
        self.assertTrue(AuditLog.objects.filter(action=AuditLog.PATIENT_CREATED).exists())

    def test_invalid_national_id_and_mobile(self):
        self.data.update(national_id="1234567890", mobile="0912")
        resp = self.client.post(reverse("patient_create"), self.data)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(Patient.objects.count(), 0)
        self.assertIn("national_id", resp.context["form"].errors)
        self.assertIn("mobile", resp.context["form"].errors)

    def test_duplicate_national_id_is_rejected(self):
        self.client.post(reverse("patient_create"), self.data)
        resp = self.client.post(reverse("patient_create"), self.data)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(Patient.objects.count(), 1)

    def test_bad_jalali_date(self):
        self.data["birth_date"] = "1405/13/40"
        resp = self.client.post(reverse("patient_create"), self.data)
        self.assertEqual(resp.status_code, 200)
        self.assertIn("birth_date", resp.context["form"].errors)

    def test_edit_logs_changes(self):
        self.client.post(reverse("patient_create"), self.data)
        patient = Patient.objects.get()
        self.data["mobile"] = "09129998877"
        resp = self.client.post(reverse("patient_edit", args=[patient.pk]), self.data)
        self.assertEqual(resp.status_code, 302)
        patient.refresh_from_db()
        self.assertEqual(patient.mobile, "09129998877")
        log = AuditLog.objects.get(action=AuditLog.PATIENT_UPDATED)
        self.assertIn("09129998877", log.details)


class VisitTests(TestCase):
    def setUp(self):
        login_as(self.client, "منشی")
        self.patient = make_patient(1)
        self.url = reverse("visit_add", args=[self.patient.pk])

    def test_add_visit_today(self):
        resp = self.client.post(self.url, {"notes": "ترمیم", "date": ""})
        self.assertEqual(resp.status_code, 302)
        visit = Visit.objects.get()
        self.assertEqual(visit.date, timezone.localdate())
        self.assertEqual(visit.notes, "ترمیم")

    def test_same_day_needs_confirmation(self):
        self.client.post(self.url, {"notes": "", "date": ""})
        resp = self.client.post(self.url, {"notes": "", "date": ""})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(Visit.objects.count(), 1)
        resp = self.client.post(self.url, {"notes": "", "date": "", "force": "1"})
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(Visit.objects.count(), 2)

    def test_future_date_rejected(self):
        resp = self.client.post(self.url, {"notes": "", "date": "1499/01/01"})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(Visit.objects.count(), 0)

    def test_external_next_is_ignored(self):
        resp = self.client.post(self.url, {"notes": "", "date": "", "next": "https://evil.example/"})
        self.assertEqual(resp.status_code, 302)
        self.assertNotIn("evil.example", resp["Location"])


class WeekTests(TestCase):
    def test_week_counts_only_current_week(self):
        login_as(self.client, "منشی")
        patient = make_patient(1)
        today = timezone.localdate()
        Visit.objects.create(patient=patient, date=today)
        Visit.objects.create(patient=patient, date=today - timedelta(days=30))
        resp = self.client.get(reverse("week"))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context["total"], 1)
        self.assertEqual(resp.context["patients_count"], 1)
