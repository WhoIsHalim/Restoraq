from __future__ import annotations

from django import forms

from core.constants import BRANCH_SCOPED_ROLES
from crm.models import Customer
from restaurants.models import Branch


class CustomerForm(forms.ModelForm):
    class Meta:
        model = Customer
        fields = ["branch", "name", "phone", "email", "notes", "loyalty_points", "is_active"]

    def __init__(self, *args, tenant=None, membership=None, language: str = "en", **kwargs):
        super().__init__(*args, **kwargs)
        self.tenant = tenant
        self.membership = membership
        self.language = (language or "en").split("-")[0]
        self.fields["branch"].queryset = self._allowed_branches()
        if membership and membership.primary_branch_id:
            self.fields["branch"].initial = membership.primary_branch_id
        if self.language == "ar":
            self.fields["branch"].label = "الفرع"
            self.fields["name"].label = "اسم العميل"
            self.fields["phone"].label = "رقم الهاتف"
            self.fields["email"].label = "البريد الإلكتروني"
            self.fields["notes"].label = "العنوان / ملاحظات"
            self.fields["loyalty_points"].label = "نقاط الولاء"
            self.fields["is_active"].label = "العميل نشط"
        for _, field in self.fields.items():
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs.setdefault("class", "form-check-input")
            elif isinstance(field.widget, forms.Select):
                field.widget.attrs.setdefault("class", "form-select")
            else:
                field.widget.attrs.setdefault("class", "form-control")

    def _allowed_branches(self):
        if not self.tenant:
            return Branch.objects.none()
        qs = Branch.objects.filter(tenant=self.tenant, is_active=True).order_by("name")
        if (
            self.membership
            and self.membership.role_name in BRANCH_SCOPED_ROLES
            and self.membership.primary_branch_id
        ):
            qs = qs.filter(id=self.membership.primary_branch_id)
        return qs
