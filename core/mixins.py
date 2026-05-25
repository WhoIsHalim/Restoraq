from __future__ import annotations

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse


class APILoginRequiredMixin(LoginRequiredMixin):
    """Return JSON auth errors for API endpoints instead of HTML redirects."""

    def handle_no_permission(self):
        if self.request.user.is_authenticated:
            return JsonResponse({"error": "forbidden"}, status=403)
        return JsonResponse({"error": "authentication_required"}, status=401)
