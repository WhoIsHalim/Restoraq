from __future__ import annotations

from django import forms

from core.constants import BRANCH_SCOPED_ROLES
from restaurants.models import Branch, DiningTable, FloorArea, Reservation


class BranchForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for _, field in self.fields.items():
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs.setdefault("class", "form-check-input")
            else:
                field.widget.attrs.setdefault("class", "form-control")

    class Meta:
        model = Branch
        fields = ["name", "code", "address", "phone", "is_active"]


class FloorAreaForm(forms.ModelForm):
    class Meta:
        model = FloorArea
        fields = ["branch", "name", "description", "is_active"]

    def __init__(self, *args, tenant=None, membership=None, **kwargs):
        super().__init__(*args, **kwargs)
        branches = Branch.objects.none()
        if tenant:
            branches = Branch.objects.filter(tenant=tenant, is_active=True)
        if membership and membership.role_name in BRANCH_SCOPED_ROLES and membership.primary_branch_id:
            branches = branches.filter(id=membership.primary_branch_id)
            self.fields["branch"].initial = membership.primary_branch_id
        self.fields["branch"].queryset = branches
        self._apply_classes()

    def _apply_classes(self):
        for _, field in self.fields.items():
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs.setdefault("class", "form-check-input")
            elif isinstance(field.widget, forms.Select):
                field.widget.attrs.setdefault("class", "form-select")
            else:
                field.widget.attrs.setdefault("class", "form-control")


class DiningTableForm(forms.ModelForm):
    class Meta:
        model = DiningTable
        fields = ["branch", "area", "name", "capacity", "is_active"]

    def __init__(self, *args, tenant=None, membership=None, **kwargs):
        super().__init__(*args, **kwargs)
        branches = Branch.objects.none()
        areas = FloorArea.objects.none()
        if tenant:
            branches = Branch.objects.filter(tenant=tenant, is_active=True)
            areas = FloorArea.objects.filter(tenant=tenant, is_active=True)
        if membership and membership.role_name in BRANCH_SCOPED_ROLES and membership.primary_branch_id:
            branches = branches.filter(id=membership.primary_branch_id)
            areas = areas.filter(branch_id=membership.primary_branch_id)
            self.fields["branch"].initial = membership.primary_branch_id
        self.fields["branch"].queryset = branches
        self.fields["area"].queryset = areas
        self._apply_classes()

    def _apply_classes(self):
        for _, field in self.fields.items():
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs.setdefault("class", "form-check-input")
            elif isinstance(field.widget, forms.Select):
                field.widget.attrs.setdefault("class", "form-select")
            else:
                field.widget.attrs.setdefault("class", "form-control")


class ReservationForm(forms.ModelForm):
    class Meta:
        model = Reservation
        fields = [
            "branch",
            "table",
            "customer_name",
            "customer_phone",
            "reservation_time",
            "party_size",
            "status",
            "source",
            "notes",
        ]
        widgets = {
            "reservation_time": forms.DateTimeInput(attrs={"type": "datetime-local"}),
        }

    def __init__(self, *args, tenant=None, membership=None, **kwargs):
        super().__init__(*args, **kwargs)
        branches = Branch.objects.none()
        tables = DiningTable.objects.none()
        if tenant:
            branches = Branch.objects.filter(tenant=tenant, is_active=True)
            tables = DiningTable.objects.filter(tenant=tenant, is_active=True)
        if membership and membership.role_name in BRANCH_SCOPED_ROLES and membership.primary_branch_id:
            branches = branches.filter(id=membership.primary_branch_id)
            tables = tables.filter(branch_id=membership.primary_branch_id)
            self.fields["branch"].initial = membership.primary_branch_id
        self.fields["branch"].queryset = branches
        self.fields["table"].queryset = tables
        self._apply_classes()

    def _apply_classes(self):
        for _, field in self.fields.items():
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs.setdefault("class", "form-check-input")
            elif isinstance(field.widget, forms.Select):
                field.widget.attrs.setdefault("class", "form-select")
            else:
                field.widget.attrs.setdefault("class", "form-control")
