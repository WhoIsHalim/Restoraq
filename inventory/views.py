from __future__ import annotations

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect
from django.urls import reverse
from django.views.generic import FormView, ListView, UpdateView

from core.constants import BRANCH_SCOPED_ROLES
from inventory.forms import IngredientForm, StockEntryForm
from inventory.models import Ingredient, LowStockAlert, StockEntry
from inventory.services import StockService


INVENTORY_WRITE_ROLES = {"RestaurantOwner", "BranchManager", "InventoryManager"}


class InventoryContextMixin(LoginRequiredMixin):
    def get_tenant(self):
        tenant = getattr(self.request, "tenant", None)
        if not tenant:
            raise PermissionDenied("Tenant context is required.")
        return tenant

    def get_membership(self):
        return getattr(self.request, "membership", None)

    def apply_branch_scope(self, queryset):
        membership = self.get_membership()
        if membership and membership.role_name in BRANCH_SCOPED_ROLES and membership.primary_branch_id:
            return queryset.filter(branch=membership.primary_branch)
        return queryset

    def can_write(self) -> bool:
        if self.request.user.is_superuser:
            return True
        membership = self.get_membership()
        return bool(membership and membership.role_name in INVENTORY_WRITE_ROLES)

    def ensure_write_access(self) -> None:
        if not self.can_write():
            raise PermissionDenied("You are not allowed to perform inventory changes.")

    def get_language(self) -> str:
        return (getattr(self.request, "LANGUAGE_CODE", "ar") or "ar").split("-")[0]


class IngredientListView(InventoryContextMixin, ListView):
    model = Ingredient
    template_name = "inventory/ingredients.html"
    context_object_name = "ingredients"
    paginate_by = 30

    def get_queryset(self):
        qs = Ingredient.objects.filter(tenant=self.get_tenant()).select_related("branch")
        return self.apply_branch_scope(qs).order_by("name")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["can_write"] = self.can_write()
        return context


class IngredientCreateView(InventoryContextMixin, FormView):
    template_name = "inventory/ingredient_form.html"
    form_class = IngredientForm

    def dispatch(self, request, *args, **kwargs):
        self.ensure_write_access()
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["tenant"] = self.get_tenant()
        kwargs["membership"] = self.get_membership()
        return kwargs

    def form_valid(self, form):
        ingredient = form.save(commit=False)
        ingredient.tenant = self.get_tenant()
        ingredient.save()
        messages.success(
            self.request,
            "تمت إضافة الصنف للمخزون بنجاح." if self.get_language() == "ar" else "Ingredient created successfully.",
        )
        return redirect("inventory:ingredients")


class IngredientUpdateView(InventoryContextMixin, UpdateView):
    model = Ingredient
    template_name = "inventory/ingredient_form.html"
    form_class = IngredientForm
    pk_url_kwarg = "pk"

    def dispatch(self, request, *args, **kwargs):
        self.ensure_write_access()
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        qs = Ingredient.objects.filter(tenant=self.get_tenant())
        return self.apply_branch_scope(qs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["tenant"] = self.get_tenant()
        kwargs["membership"] = self.get_membership()
        return kwargs

    def form_valid(self, form):
        messages.success(
            self.request,
            "تم تحديث صنف المخزون بنجاح." if self.get_language() == "ar" else "Ingredient updated successfully.",
        )
        return super().form_valid(form)

    def get_success_url(self):
        return redirect("inventory:ingredients").url


class StockEntryListView(InventoryContextMixin, ListView):
    model = StockEntry
    template_name = "inventory/stock_entries.html"
    context_object_name = "entries"
    paginate_by = 30

    def get_queryset(self):
        qs = StockEntry.objects.filter(tenant=self.get_tenant()).select_related("ingredient", "supplier", "branch")
        return self.apply_branch_scope(qs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["can_write"] = self.can_write()
        return context


class StockEntryCreateView(InventoryContextMixin, FormView):
    template_name = "inventory/stock_entry_form.html"
    form_class = StockEntryForm

    def dispatch(self, request, *args, **kwargs):
        self.ensure_write_access()
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["tenant"] = self.get_tenant()
        kwargs["membership"] = self.get_membership()
        return kwargs

    def form_valid(self, form):
        ingredient = form.cleaned_data["ingredient"]
        branch = form.cleaned_data["branch"]
        StockService.record_entry(
            tenant=self.get_tenant(),
            branch=branch,
            ingredient=ingredient,
            movement_type=form.cleaned_data["movement_type"],
            quantity=form.cleaned_data["quantity"],
            actor=self.request.user,
            reference=form.cleaned_data["reference"],
            note=form.cleaned_data["note"],
        )
        messages.success(
            self.request,
            "تم تسجيل حركة المخزون بنجاح." if self.get_language() == "ar" else "Stock entry recorded successfully.",
        )
        return redirect("inventory:stock-entries")


class LowStockAlertListView(InventoryContextMixin, ListView):
    model = LowStockAlert
    template_name = "inventory/alerts.html"
    context_object_name = "alerts"
    paginate_by = 30

    def get_queryset(self):
        qs = LowStockAlert.objects.filter(tenant=self.get_tenant()).select_related("ingredient", "branch")
        return self.apply_branch_scope(qs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["can_write"] = self.can_write()
        context["new_entry_url"] = reverse("inventory:stock-entry-create")
        return context
