from __future__ import annotations

from django.shortcuts import resolve_url
from django.utils.http import url_has_allowed_host_and_scheme


def safe_redirect_target(request, target: str | None, fallback: str) -> str:
    resolved_fallback = resolve_url(fallback)
    if not target:
        return resolved_fallback
    allowed_hosts = {request.get_host()} if request else set()
    if url_has_allowed_host_and_scheme(
        url=target,
        allowed_hosts=allowed_hosts,
        require_https=request.is_secure() if request else False,
    ):
        return target
    return resolved_fallback
