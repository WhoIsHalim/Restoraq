from __future__ import annotations

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect
from django.views import View
from django.views.generic import FormView, ListView, UpdateView

from core.policies import AccessPolicy
from core.constants import BRANCH_SCOPED_ROLES
from restaurants.forms import BranchForm, DiningTableForm, FloorAreaForm, ReservationForm
from restaurants.models import Branch, DiningTable, FloorArea, Reservation


BRANCH_WRITE_ROLES = {"RestaurantOwner", "BranchManager"}
TABLE_WRITE_ROLES = {"RestaurantOwner", "BranchManager"}
RESERVATION_WRITE_ROLES = {"RestaurantOwner", "BranchManager", "Cashier"}


class BranchContextMixin(LoginRequiredMixin):
    write_roles = BRANCH_WRITE_ROLES
    def get_tenant(self):
        tenant = getattr(self.request, "tenant", None)
        if not tenant:
            raise PermissionDenied("Tenant context is required.")
        return tenant

    def get_membership(self):
        return getattr(self.request, "membership", None)

    def can_write(self):
        if self.request.user.is_superuser:
            return True
        membership = self.get_membership()
        return bool(membership and membership.role_name in set(self.write_roles))

    def ensure_write_access(self):
        if not self.can_write():
            raise PermissionDenied("You are not allowed to manage branches.")

    def get_language(self) -> str:
        return (getattr(self.request, "LANGUAGE_CODE", "ar") or "ar").split("-")[0]

    def apply_branch_scope(self, queryset):
        membership = self.get_membership()
        if membership and membership.role_name in BRANCH_SCOPED_ROLES and membership.primary_branch_id:
            return queryset.filter(branch_id=membership.primary_branch_id)
        return queryset


class BranchListView(BranchContextMixin, ListView):
    model = Branch
    template_name = "restaurants/branches.html"
    context_object_name = "branches"
    paginate_by = 30

    def get_queryset(self):
        return Branch.objects.filter(tenant=self.get_tenant()).order_by("name")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["can_write"] = self.can_write()
        return context


class BranchCreateView(BranchContextMixin, FormView):
    template_name = "restaurants/branch_form.html"
    form_class = BranchForm

    def dispatch(self, request, *args, **kwargs):
        self.ensure_write_access()
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        branch = form.save(commit=False)
        branch.tenant = self.get_tenant()
        branch.save()
        messages.success(
            self.request,
            "تم إضافة فرع جديد بنجاح." if self.get_language() == "ar" else "Branch created successfully.",
        )
        return redirect("restaurants:branches")


class BranchUpdateView(BranchContextMixin, UpdateView):
    model = Branch
    template_name = "restaurants/branch_form.html"
    form_class = BranchForm
    pk_url_kwarg = "pk"

    def dispatch(self, request, *args, **kwargs):
        self.ensure_write_access()
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return Branch.objects.filter(tenant=self.get_tenant())

    def form_valid(self, form):
        messages.success(
            self.request,
            "تم تحديث بيانات الفرع بنجاح." if self.get_language() == "ar" else "Branch updated successfully.",
        )
        return super().form_valid(form)

    def get_success_url(self):
        return redirect("restaurants:branches").url


class RestaurantCreateRedirectView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        if not AccessPolicy.is_system_user(request.user):
            raise PermissionDenied("You are not allowed to create restaurants.")
        return redirect("system:tenant-create")


class FloorAreaListView(BranchContextMixin, ListView):
    model = FloorArea
    template_name = "restaurants/floor_areas.html"
    context_object_name = "areas"
    paginate_by = 30
    write_roles = TABLE_WRITE_ROLES

    def get_queryset(self):
        qs = FloorArea.objects.filter(tenant=self.get_tenant()).select_related("branch")
        return self.apply_branch_scope(qs).order_by("name")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["can_write"] = self.can_write()
        return context


class FloorAreaCreateView(BranchContextMixin, FormView):
    template_name = "restaurants/floor_area_form.html"
    form_class = FloorAreaForm
    write_roles = TABLE_WRITE_ROLES

    def dispatch(self, request, *args, **kwargs):
        self.ensure_write_access()
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["tenant"] = self.get_tenant()
        kwargs["membership"] = self.get_membership()
        return kwargs

    def form_valid(self, form):
        area = form.save(commit=False)
        area.tenant = self.get_tenant()
        area.save()
        messages.success(
            self.request,
            "تم إنشاء منطقة الجلوس بنجاح." if self.get_language() == "ar" else "Floor area created successfully.",
        )
        return redirect("restaurants:floor-areas")


class FloorAreaUpdateView(BranchContextMixin, UpdateView):
    model = FloorArea
    template_name = "restaurants/floor_area_form.html"
    form_class = FloorAreaForm
    pk_url_kwarg = "pk"
    write_roles = TABLE_WRITE_ROLES

    def dispatch(self, request, *args, **kwargs):
        self.ensure_write_access()
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        qs = FloorArea.objects.filter(tenant=self.get_tenant())
        return self.apply_branch_scope(qs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["tenant"] = self.get_tenant()
        kwargs["membership"] = self.get_membership()
        return kwargs

    def form_valid(self, form):
        messages.success(
            self.request,
            "تم تحديث منطقة الجلوس." if self.get_language() == "ar" else "Floor area updated.",
        )
        return super().form_valid(form)

    def get_success_url(self):
        return redirect("restaurants:floor-areas").url


class DiningTableListView(BranchContextMixin, ListView):
    model = DiningTable
    template_name = "restaurants/tables.html"
    context_object_name = "tables"
    paginate_by = 30
    write_roles = TABLE_WRITE_ROLES

    def get_queryset(self):
        qs = DiningTable.objects.filter(tenant=self.get_tenant()).select_related("branch", "area")
        return self.apply_branch_scope(qs).order_by("name")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["can_write"] = self.can_write()
        return context


class DiningTableCreateView(BranchContextMixin, FormView):
    template_name = "restaurants/table_form.html"
    form_class = DiningTableForm
    write_roles = TABLE_WRITE_ROLES

    def dispatch(self, request, *args, **kwargs):
        self.ensure_write_access()
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["tenant"] = self.get_tenant()
        kwargs["membership"] = self.get_membership()
        return kwargs

    def form_valid(self, form):
        table = form.save(commit=False)
        table.tenant = self.get_tenant()
        table.save()
        messages.success(
            self.request,
            "تم إنشاء الطاولة بنجاح." if self.get_language() == "ar" else "Table created successfully.",
        )
        return redirect("restaurants:tables")


class DiningTableUpdateView(BranchContextMixin, UpdateView):
    model = DiningTable
    template_name = "restaurants/table_form.html"
    form_class = DiningTableForm
    pk_url_kwarg = "pk"
    write_roles = TABLE_WRITE_ROLES

    def dispatch(self, request, *args, **kwargs):
        self.ensure_write_access()
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        qs = DiningTable.objects.filter(tenant=self.get_tenant())
        return self.apply_branch_scope(qs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["tenant"] = self.get_tenant()
        kwargs["membership"] = self.get_membership()
        return kwargs

    def form_valid(self, form):
        messages.success(
            self.request,
            "تم تحديث بيانات الطاولة." if self.get_language() == "ar" else "Table updated successfully.",
        )
        return super().form_valid(form)

    def get_success_url(self):
        return redirect("restaurants:tables").url


class ReservationListView(BranchContextMixin, ListView):
    model = Reservation
    template_name = "restaurants/reservations.html"
    context_object_name = "reservations"
    paginate_by = 30
    write_roles = RESERVATION_WRITE_ROLES

    def get_queryset(self):
        qs = Reservation.objects.filter(tenant=self.get_tenant()).select_related("branch", "table")
        return self.apply_branch_scope(qs).order_by("-reservation_time")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["can_write"] = self.can_write()
        return context


class ReservationCreateView(BranchContextMixin, FormView):
    template_name = "restaurants/reservation_form.html"
    form_class = ReservationForm
    write_roles = RESERVATION_WRITE_ROLES

    def dispatch(self, request, *args, **kwargs):
        self.ensure_write_access()
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["tenant"] = self.get_tenant()
        kwargs["membership"] = self.get_membership()
        return kwargs

    def form_valid(self, form):
        reservation = form.save(commit=False)
        reservation.tenant = self.get_tenant()
        reservation.save()
        messages.success(
            self.request,
            "تم تسجيل الحجز." if self.get_language() == "ar" else "Reservation created successfully.",
        )
        return redirect("restaurants:reservations")


class ReservationUpdateView(BranchContextMixin, UpdateView):
    model = Reservation
    template_name = "restaurants/reservation_form.html"
    form_class = ReservationForm
    pk_url_kwarg = "pk"
    write_roles = RESERVATION_WRITE_ROLES

    def dispatch(self, request, *args, **kwargs):
        self.ensure_write_access()
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        qs = Reservation.objects.filter(tenant=self.get_tenant())
        return self.apply_branch_scope(qs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["tenant"] = self.get_tenant()
        kwargs["membership"] = self.get_membership()
        return kwargs

    def form_valid(self, form):
        messages.success(
            self.request,
            "تم تحديث الحجز." if self.get_language() == "ar" else "Reservation updated successfully.",
        )
        return super().form_valid(form)

    def get_success_url(self):
        return redirect("restaurants:reservations").url
