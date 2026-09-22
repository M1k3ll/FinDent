from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.contrib.messages.views import SuccessMessageMixin
from django.urls import include, path, reverse_lazy


class PasswordChange(SuccessMessageMixin, auth_views.PasswordChangeView):
    template_name = "registration/password_change.html"
    success_url = reverse_lazy("home")
    success_message = "رمز عبور تغییر کرد."


urlpatterns = [
    path("admin/", admin.site.urls),
    path("login/", auth_views.LoginView.as_view(redirect_authenticated_user=True), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("password/", PasswordChange.as_view(), name="password_change"),
    path("", include("patients.urls")),
]

admin.site.site_header = "Findent: مدیریت"
admin.site.site_title = "Findent"
admin.site.index_title = "مدیریت کاربران و داده‌ها"
