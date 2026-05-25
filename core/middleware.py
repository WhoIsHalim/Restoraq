from __future__ import annotations

import uuid

from django.conf import settings


class RequestContextMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.request_id = str(uuid.uuid4())
        request.client_ip = self._extract_ip(request)
        request.client_device = request.META.get("HTTP_USER_AGENT", "unknown")[:255]
        response = self.get_response(request)
        response["X-Request-ID"] = request.request_id
        return response

    @staticmethod
    def _extract_ip(request) -> str:
        forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR", "0.0.0.0")


class DefaultLanguageCookieMiddleware:
    """
    Force Arabic as the first-visit default language regardless of browser locale.
    LocaleMiddleware reads from LANGUAGE_COOKIE_NAME first, so we ensure it exists.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        cookie_name = settings.LANGUAGE_COOKIE_NAME
        supported_languages = {code for code, _ in settings.LANGUAGES}
        cookie_lang = request.COOKIES.get(cookie_name)
        if cookie_lang not in supported_languages:
            request.COOKIES[cookie_name] = settings.LANGUAGE_CODE
            request._set_default_language_cookie = True

        response = self.get_response(request)

        if getattr(request, "_set_default_language_cookie", False):
            response.set_cookie(
                cookie_name,
                request.COOKIES[cookie_name],
                max_age=365 * 24 * 60 * 60,
                secure=getattr(settings, "LANGUAGE_COOKIE_SECURE", settings.SESSION_COOKIE_SECURE),
                samesite=getattr(settings, "LANGUAGE_COOKIE_SAMESITE", "Strict"),
            )
        return response


class ContentSecurityPolicyMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        policy = getattr(settings, "CONTENT_SECURITY_POLICY", "")
        if policy and "Content-Security-Policy" not in response:
            response["Content-Security-Policy"] = policy
        return response
