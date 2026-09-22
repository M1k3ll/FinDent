from django.urls import path

from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("search/", views.search, name="search"),
    path("patients/new/", views.patient_create, name="patient_create"),
    path("patients/<int:pk>/", views.patient_detail, name="patient_detail"),
    path("patients/<int:pk>/edit/", views.patient_edit, name="patient_edit"),
    path("patients/<int:pk>/visit/", views.visit_add, name="visit_add"),
    path("visits/<int:pk>/edit/", views.visit_edit, name="visit_edit"),
    path("visits/<int:pk>/delete/", views.visit_delete, name="visit_delete"),
    path("week/", views.week_visits, name="week"),
    path("settings/", views.settings_page, name="settings"),
    path("settings/log/", views.audit_log, name="audit_log"),
    path("about/", views.about, name="about"),
]
