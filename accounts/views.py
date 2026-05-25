from __future__ import annotations

from django.conf import settings
from django.contrib.auth import logout as auth_logout
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView
from django.shortcuts import redirect
from django.urls import reverse
from django.utils import translation
from django.views import View
from django.views.generic import TemplateView

from accounts.forms import LoginForm
from core.utils import safe_redirect_target


class UserLoginView(LoginView):
    template_name = "accounts/login.html"
    form_class = LoginForm

    def get_success_url(self):
        redirect_to = self.get_redirect_url()
        if redirect_to:
            return redirect_to
        user = self.request.user
        if user.is_superuser or user.groups.filter(name__in={"SystemOwner", "SystemAdmin", "ContentManager"}).exists():
            return reverse("system:dashboard")
        return reverse("core:dashboard")

    def form_valid(self, form):
        response = super().form_valid(form)
        user = form.get_user()
        language_code = user.preferred_language if user.preferred_language in {"ar", "en"} else "ar"
        translation.activate(language_code)
        response.set_cookie(
            settings.LANGUAGE_COOKIE_NAME,
            language_code,
            max_age=365 * 24 * 60 * 60,
            secure=getattr(settings, "LANGUAGE_COOKIE_SECURE", settings.SESSION_COOKIE_SECURE),
            samesite=getattr(settings, "LANGUAGE_COOKIE_SAMESITE", "Strict"),
        )
        return response


class UserLogoutView(View):
    http_method_names = ["get", "post", "options"]

    def get(self, request, *args, **kwargs):
        return self.post(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        auth_logout(request)
        return redirect("accounts:login")


class ProfileView(LoginRequiredMixin, TemplateView):
    template_name = "accounts/profile.html"


def switch_language(request, language_code: str):
    if language_code not in {"ar", "en"}:
        language_code = "ar"
    translation.activate(language_code)
    target = safe_redirect_target(request, request.META.get("HTTP_REFERER"), "core:home")
    response = redirect(target)
    response.set_cookie(
        settings.LANGUAGE_COOKIE_NAME,
        language_code,
        max_age=365 * 24 * 60 * 60,
        secure=getattr(settings, "LANGUAGE_COOKIE_SECURE", settings.SESSION_COOKIE_SECURE),
        samesite=getattr(settings, "LANGUAGE_COOKIE_SAMESITE", "Strict"),
    )
    if request.user.is_authenticated:
        request.user.preferred_language = language_code
        request.user.save(update_fields=["preferred_language"])
    return response
