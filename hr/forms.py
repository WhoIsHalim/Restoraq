from __future__ import annotations

from django import forms

from core.constants import BRANCH_SCOPED_ROLES
from hr.models import Employee
from restaurants.models import Branch


class EmployeeForm(forms.ModelForm):
    class Meta:
        model = Employee
        fields = [
            "branch",
            "full_name",
            "phone",
            "email",
            "position",
            "salary",
            "hired_on",
            "is_active",
        ]
        widgets = {
            "hired_on": forms.DateInput(attrs={"type": "date"}),
        }

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
