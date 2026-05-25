from __future__ import annotations

import json

from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.http import HttpRequest, HttpResponseBadRequest, JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.views import View
from django.views.generic import DetailView, ListView, TemplateView, UpdateView

from core.mixins import APILoginRequiredMixin
from core.policies import AccessPolicy
from featureflags.services import FeatureService
from orders.forms import OrderEditForm, OrderItemFormSet
from orders.models import Order, PaymentReview
from orders.services import OrderService


class OrderListView(LoginRequiredMixin, ListView):
    model = Order
    template_name = "orders/list.html"
    context_object_name = "orders"
    paginate_by = 30

    def get_queryset(self):
        AccessPolicy.require_membership(self.request)
        tenant = getattr(self.request, "tenant", None)
        qs = Order.objects.select_related("branch").prefetch_related("items", "payments")
        if tenant:
            qs = qs.filter(tenant=tenant)
        qs = AccessPolicy.apply_branch_scope(self.request, qs)
        return qs


class OrderDetailView(LoginRequiredMixin, DetailView):
    model = Order
    template_name = "orders/detail.html"
    context_object_name = "order"
    pk_url_kwarg = "pk"

    def get_queryset(self):
        AccessPolicy.require_membership(self.request)
        qs = Order.objects.filter(tenant=getattr(self.request, "tenant", None)).select_related("branch", "created_by")
        qs = qs.prefetch_related("items__product", "payments")
        return AccessPolicy.apply_branch_scope(self.request, qs)


class OrderCreateAPIView(APILoginRequiredMixin, View):
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
            order = OrderService.create_order(
                tenant=tenant,
                branch=branch,
                user=request.user,
                payload=payload,
                source=payload.get("source", "online"),
            )
        except Exception as exc:
            return HttpResponseBadRequest(str(exc))

        return JsonResponse(
            {
                "id": order.id,
                "order_number": order.order_number,
                "status": order.status,
                "total": str(order.total_amount),
                "pending_sync": order.pending_sync,
            }
        )


class PaymentReviewQueueAPIView(APILoginRequiredMixin, View):
    def get(self, request):
        tenant = getattr(request, "tenant", None)
        if not tenant:
            return JsonResponse({"results": []})
        rows = PaymentReview.objects.filter(
            tenant=tenant,
            status=PaymentReview.STATUS_PENDING,
        ).select_related("payment", "payment__order")
        rows = AccessPolicy.apply_branch_scope(request, rows)
        payload = [
            {
                "review_id": row.id,
                "order_number": row.payment.order.order_number,
                "payment_method": row.payment.method,
                "amount": str(row.payment.amount),
            }
            for row in rows
        ]
        return JsonResponse({"results": payload})


class OrderUpdateView(LoginRequiredMixin, UpdateView):
    model = Order
    template_name = "orders/edit.html"
    form_class = OrderEditForm
    pk_url_kwarg = "pk"

    def dispatch(self, request, *args, **kwargs):
        AccessPolicy.require_membership(request)
        if not AccessPolicy.has_any_role(request, {"RestaurantOwner", "BranchManager", "Cashier", "SystemOwner", "SystemAdmin"}):
            raise PermissionDenied("You are not allowed to edit orders.")
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        qs = Order.objects.filter(tenant=getattr(self.request, "tenant", None))
        return AccessPolicy.apply_branch_scope(self.request, qs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        order = self.object
        if self.request.method == "POST":
            context["item_formset"] = OrderItemFormSet(self.request.POST, queryset=order.items.select_related("product").all(), prefix="items")
        else:
            context["item_formset"] = OrderItemFormSet(queryset=order.items.select_related("product").all(), prefix="items")
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        item_formset = context["item_formset"]
        if not item_formset.is_valid():
            return self.form_invalid(form)
        self.object = form.save()
        item_formset.save()
        OrderService.recalculate_order_totals(order=self.object)
        return redirect("orders:detail", pk=self.object.pk)

    def form_invalid(self, form):
        return self.render_to_response(self.get_context_data(form=form))


class OrderReopenView(LoginRequiredMixin, View):
    def post(self, request, pk: int):
        AccessPolicy.require_order_write_access(request)
        order_qs = Order.objects.filter(pk=pk, tenant=getattr(request, "tenant", None))
        order_qs = AccessPolicy.apply_branch_scope(request, order_qs)
        order = get_object_or_404(order_qs)
        order.status = Order.STATUS_DRAFT
        order.kitchen_status = Order.KITCHEN_PENDING
        order.kitchen_started_at = None
        order.kitchen_completed_at = None
        order.cooking_duration_minutes = None
        order.save(
            update_fields=[
                "status",
                "kitchen_status",
                "kitchen_started_at",
                "kitchen_completed_at",
                "cooking_duration_minutes",
                "updated_at",
            ]
        )
        return redirect("orders:detail", pk=order.pk)


class KitchenBoardView(LoginRequiredMixin, TemplateView):
    template_name = "orders/kitchen_board.html"

    def dispatch(self, request, *args, **kwargs):
        ctx = AccessPolicy.require_kitchen_access(request)
        tenant = ctx.tenant
        if not tenant:
            raise PermissionDenied("Tenant context is required.")
        if not FeatureService.is_enabled(tenant, "kds_screen"):
            raise PermissionDenied("Kitchen display is not enabled for your plan.")
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        tenant = getattr(self.request, "tenant", None)
        membership = getattr(self.request, "membership", None)

        queue = Order.objects.filter(
            tenant=tenant,
            kitchen_status__in=[Order.KITCHEN_PENDING, Order.KITCHEN_PREPARING],
        ).select_related("branch").prefetch_related("items")
        if membership and membership.primary_branch_id:
            queue = queue.filter(branch_id=membership.primary_branch_id)

        context["queue_orders"] = queue.order_by("created_at")
        return context


class KitchenStatusUpdateView(LoginRequiredMixin, View):
    def post(self, request, order_id: int):
        ctx = AccessPolicy.require_kitchen_access(request)
        tenant = ctx.tenant
        membership = ctx.membership
        if not tenant:
            return HttpResponseBadRequest("Tenant context is required")
        if not FeatureService.is_enabled(tenant, "kds_screen"):
            return HttpResponseBadRequest("Kitchen display is not enabled for your plan")

        status = request.POST.get("kitchen_status", "").strip()
        order_qs = Order.objects.filter(id=order_id, tenant=tenant)
        if membership and membership.primary_branch_id:
            order_qs = order_qs.filter(branch_id=membership.primary_branch_id)
        order = order_qs.first()
        if not order:
            return HttpResponseBadRequest("Order not found")

        try:
            updated = OrderService.set_kitchen_status(order=order, actor=request.user, kitchen_status=status)
        except Exception as exc:
            return HttpResponseBadRequest(str(exc))
        return JsonResponse(
            {
                "id": updated.id,
                "order_number": updated.order_number,
                "kitchen_status": updated.kitchen_status,
                "cooking_duration_minutes": updated.cooking_duration_minutes,
            }
        )
