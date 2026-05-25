from __future__ import annotations

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect
from django.views.generic import FormView, ListView, UpdateView

from core.constants import BRANCH_SCOPED_ROLES
from hr.forms import EmployeeForm
from hr.models import Employee


HR_WRITE_ROLES = {"RestaurantOwner", "BranchManager"}


class HRContextMixin(LoginRequiredMixin):
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
            return queryset.filter(branch_id=membership.primary_branch_id)
        return queryset

    def can_write(self):
        if self.request.user.is_superuser:
            return True
        membership = self.get_membership()
        return bool(membership and membership.role_name in HR_WRITE_ROLES)

    def ensure_write_access(self):
        if not self.can_write():
            raise PermissionDenied("You are not allowed to modify employees.")


class EmployeeListView(HRContextMixin, ListView):
    model = Employee
    template_name = "hr/employees.html"
    context_object_name = "employees"
    paginate_by = 30

    def get_queryset(self):
        qs = Employee.objects.filter(tenant=self.get_tenant()).select_related("branch")
        return self.apply_branch_scope(qs).order_by("full_name")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["can_write"] = self.can_write()
        return context


class EmployeeCreateView(HRContextMixin, FormView):
    template_name = "hr/employee_form.html"
    form_class = EmployeeForm

    def dispatch(self, request, *args, **kwargs):
        self.ensure_write_access()
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["tenant"] = self.get_tenant()
        kwargs["membership"] = self.get_membership()
        return kwargs

    def form_valid(self, form):
        employee = form.save(commit=False)
        employee.tenant = self.get_tenant()
        employee.save()
        messages.success(
            self.request,
            "تمت إضافة الموظف بنجاح." if self.request.LANGUAGE_CODE.startswith("ar") else "Employee created successfully.",
        )
        return redirect("hr:employees")


class EmployeeUpdateView(HRContextMixin, UpdateView):
    model = Employee
    template_name = "hr/employee_form.html"
    form_class = EmployeeForm
    pk_url_kwarg = "pk"

    def dispatch(self, request, *args, **kwargs):
        self.ensure_write_access()
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        qs = Employee.objects.filter(tenant=self.get_tenant())
        return self.apply_branch_scope(qs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["tenant"] = self.get_tenant()
        kwargs["membership"] = self.get_membership()
        return kwargs

    def form_valid(self, form):
        messages.success(
            self.request,
            "تم تحديث بيانات الموظف." if self.request.LANGUAGE_CODE.startswith("ar") else "Employee updated successfully.",
        )
        return super().form_valid(form)

    def get_success_url(self):
        return redirect("hr:employees").url
