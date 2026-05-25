from __future__ import annotations


class AuditContextMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.audit_context = {
            "ip": getattr(request, "client_ip", None),
            "device": getattr(request, "client_device", ""),
            "request_id": getattr(request, "request_id", ""),
        }
        return self.get_response(request)
