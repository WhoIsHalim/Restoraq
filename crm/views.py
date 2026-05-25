from __future__ import annotations

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.shortcuts import redirect
from django.views.generic import DetailView, ListView, UpdateView
from django.views.generic.edit import FormView

from core.policies import AccessPolicy
from crm.forms import CustomerForm
from crm.models import Customer
from orders.models import Order


CRM_WRITE_ROLES = {"RestaurantOwner", "BranchManager", "Cashier", "Accountant", "SystemOwner", "SystemAdmin"}


class CRMContextMixin(LoginRequiredMixin):
    def get_tenant(self):
        tenant = getattr(self.request, "tenant", None)
        if not tenant:
            raise PermissionDenied("Tenant context is required.")
        return tenant

    def get_membership(self):
        return getattr(self.request, "membership", None)

    def can_write(self) -> bool:
        if self.request.user.is_superuser:
            return True
        membership = self.get_membership()
        return bool(membership and membership.role_name in CRM_WRITE_ROLES)

    def ensure_can_write(self):
        if not self.can_write():
            raise PermissionDenied("You are not allowed to modify customers.")


class CustomerListView(CRMContextMixin, ListView):
    model = Customer
    template_name = "crm/customers.html"
    context_object_name = "customers"
    paginate_by = 30

    def get_queryset(self):
        qs = Customer.objects.filter(tenant=self.get_tenant()).select_related("branch")
        qs = AccessPolicy.apply_branch_scope(self.request, qs)
        query = (self.request.GET.get("q") or "").strip()
        if query:
            qs = qs.filter(Q(name__icontains=query) | Q(phone__icontains=query))
        return qs.order_by("name")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["can_write"] = self.can_write()
        context["q"] = (self.request.GET.get("q") or "").strip()
        return context


class CustomerDetailView(CRMContextMixin, DetailView):
    model = Customer
    template_name = "crm/customer_detail.html"
    context_object_name = "customer"
    pk_url_kwarg = "pk"

    def get_queryset(self):
        qs = Customer.objects.filter(tenant=self.get_tenant()).select_related("branch")
        return AccessPolicy.apply_branch_scope(self.request, qs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        customer = self.object
        orders = Order.objects.filter(tenant=self.get_tenant(), customer=customer).select_related("branch")
        orders = AccessPolicy.apply_branch_scope(self.request, orders)
        context["orders"] = orders.order_by("-created_at")
        context["can_write"] = self.can_write()
        return context


class CustomerCreateView(CRMContextMixin, FormView):
    template_name = "crm/customer_form.html"
    form_class = CustomerForm

    def dispatch(self, request, *args, **kwargs):
        self.ensure_can_write()
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["tenant"] = self.get_tenant()
        kwargs["membership"] = self.get_membership()
        kwargs["language"] = getattr(self.request, "LANGUAGE_CODE", "en")
        return kwargs

    def form_valid(self, form):
        customer = form.save(commit=False)
        customer.tenant = self.get_tenant()
        customer.save()
        messages.success(
            self.request,
            "تم إنشاء عميل جديد." if self.request.LANGUAGE_CODE.startswith("ar") else "Customer created successfully.",
        )
        return redirect("crm:customer-detail", pk=customer.id)


class CustomerUpdateView(CRMContextMixin, UpdateView):
    model = Customer
    template_name = "crm/customer_form.html"
    form_class = CustomerForm
    pk_url_kwarg = "pk"

    def dispatch(self, request, *args, **kwargs):
        self.ensure_can_write()
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        qs = Customer.objects.filter(tenant=self.get_tenant())
        return AccessPolicy.apply_branch_scope(self.request, qs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["tenant"] = self.get_tenant()
        kwargs["membership"] = self.get_membership()
        kwargs["language"] = getattr(self.request, "LANGUAGE_CODE", "en")
        return kwargs

    def form_valid(self, form):
        messages.success(
            self.request,
            "تم تحديث بيانات العميل." if self.request.LANGUAGE_CODE.startswith("ar") else "Customer updated successfully.",
        )
        return super().form_valid(form)

    def get_success_url(self):
        return redirect("crm:customer-detail", pk=self.object.pk).url
