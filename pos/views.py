from __future__ import annotations

import json

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpRequest, HttpResponseBadRequest, JsonResponse
from django.utils.decorators import method_decorator
from django.template.response import TemplateResponse
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views import View
from django.views.generic import TemplateView

from core.constants import BRANCH_SCOPED_ROLES
from core.mixins import APILoginRequiredMixin
from core.policies import AccessPolicy
from crm.models import Customer
from menu.services import MenuService
from orders.models import Order
from orders.services import OrderService
from pos.services import POSService


@method_decorator(ensure_csrf_cookie, name="dispatch")
class POSTerminalView(LoginRequiredMixin, TemplateView):
    template_name = "pos/terminal.html"

    def dispatch(self, request, *args, **kwargs):
        AccessPolicy.require_pos_access(request)
        return super().dispatch(request, *args, **kwargs)


class POSSyncStatusFragmentView(LoginRequiredMixin, View):
    def get(self, request):
        AccessPolicy.require_pos_access(request)
        tenant = getattr(request, "tenant", None)
        branch = AccessPolicy.resolve_operating_branch(request, tenant=tenant, requested_branch_id=request.GET.get("branch_id"))
        pending_sync_count = 0
        if tenant:
            qs = Order.objects.filter(tenant=tenant, pending_sync=True)
            if branch:
                qs = qs.filter(branch=branch)
            pending_sync_count = qs.count()
        return TemplateResponse(
            request,
            "pos/_sync_status.html",
            {"pending_sync_count": pending_sync_count},
        )


class POSMenuPayloadAPIView(APILoginRequiredMixin, View):
    def get(self, request):
        ctx = AccessPolicy.require_pos_access(request)
        tenant = getattr(request, "tenant", None)
        if not tenant:
            return JsonResponse(
                {"categories": [], "products": [], "active_branch_id": None, "branches": [], "branch_locked": False}
            )
        branch = AccessPolicy.resolve_operating_branch(request, tenant=tenant, requested_branch_id=request.GET.get("branch_id"))
        payload = MenuService.build_menu_payload(tenant=tenant, branch=branch)
        payload["active_branch_id"] = getattr(branch, "id", None)
        payload["branches"] = [
            {"id": b.id, "name": b.name}
            for b in AccessPolicy.permitted_branches(request, tenant=tenant)
        ]
        payload["branch_locked"] = bool(ctx.membership and ctx.role_name in BRANCH_SCOPED_ROLES)
        for product in payload.get("products", []):
            image_path = product.get("image") or ""
            if image_path:
                try:
                    product["image"] = request.build_absolute_uri(image_path)
                except Exception:
                    product["image"] = image_path
            else:
                product["image"] = ""
        return JsonResponse(payload)


class POSOrderPreviewAPIView(APILoginRequiredMixin, View):
    def post(self, request: HttpRequest):
        ctx = AccessPolicy.require_order_write_access(request)
        tenant = ctx.tenant
        if not tenant:
            return HttpResponseBadRequest("Tenant context required")

        try:
            payload = json.loads(request.body.decode("utf-8"))
        except json.JSONDecodeError:
            return HttpResponseBadRequest("Invalid JSON")
        branch = AccessPolicy.resolve_operating_branch(
            request,
            tenant=tenant,
            requested_branch_id=payload.get("branch_id"),
        )
        if not branch:
            return HttpResponseBadRequest("Branch context required")
        try:
            totals = OrderService.preview_order(tenant=tenant, branch=branch, items=payload.get("items", []))
        except Exception as exc:
            return HttpResponseBadRequest(str(exc))

        return JsonResponse(
            {
                "subtotal": str(totals.subtotal),
                "tax": str(totals.tax),
                "total": str(totals.total),
            }
        )


class POSSyncOrdersAPIView(APILoginRequiredMixin, View):
    def post(self, request: HttpRequest):
        ctx = AccessPolicy.require_order_write_access(request)
        tenant = ctx.tenant
        if not tenant:
            return HttpResponseBadRequest("Tenant context required")

        try:
            payload = json.loads(request.body.decode("utf-8"))
        except json.JSONDecodeError:
            return HttpResponseBadRequest("Invalid JSON")

        rows = payload.get("orders", [])
        synced = []
        errors = []
        for row in rows:
            try:
                branch = AccessPolicy.resolve_operating_branch(
                    request,
                    tenant=tenant,
                    requested_branch_id=row.get("branch_id"),
                )
                if not branch:
                    raise ValueError("Branch context required")
                order = OrderService.create_order(
                    tenant=tenant,
                    branch=branch,
                    user=request.user,
                    payload=row,
                    source="offline",
                )
                synced.append(POSService.build_status_payload(order))
            except Exception as exc:
                errors.append({"client_order_uuid": row.get("client_order_uuid"), "error": str(exc)})

        return JsonResponse({"synced": synced, "errors": errors})


class POSCustomerLookupAPIView(APILoginRequiredMixin, View):
    def get(self, request):
        AccessPolicy.require_pos_access(request)
        tenant = getattr(request, "tenant", None)
        if not tenant:
            return JsonResponse({"results": []})
        branch = AccessPolicy.resolve_operating_branch(
            request,
            tenant=tenant,
            requested_branch_id=request.GET.get("branch_id"),
        )
        phone = (request.GET.get("phone") or "").strip()
        q = (request.GET.get("q") or "").strip()
        qs = Customer.objects.filter(tenant=tenant, is_active=True)
        if branch:
            qs = qs.filter(branch__in=[branch, None])
        if phone:
            qs = qs.filter(phone__icontains=phone)
        elif q:
            qs = qs.filter(name__icontains=q)
        else:
            qs = qs.order_by("-updated_at")
        rows = [
            {
                "id": row.id,
                "name": row.name,
                "phone": row.phone,
                "address": row.notes or "",
            }
            for row in qs.order_by("name")[:20]
        ]
        return JsonResponse({"results": rows})


class POSOrderStatusAPIView(APILoginRequiredMixin, View):
    def get(self, request, order_id: int):
        AccessPolicy.require_pos_access(request)
        tenant = getattr(request, "tenant", None)
        order_qs = Order.objects.filter(id=order_id, tenant=tenant)
        order_qs = AccessPolicy.apply_branch_scope(request, order_qs)
        order = order_qs.first()
        if not order:
            return HttpResponseBadRequest("Order not found")
        return JsonResponse(POSService.build_status_payload(order))
