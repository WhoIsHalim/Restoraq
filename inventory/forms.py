from __future__ import annotations

from django import forms

from core.constants import BRANCH_SCOPED_ROLES
from inventory.models import Ingredient, StockEntry
from restaurants.models import Branch


class IngredientForm(forms.ModelForm):
    class Meta:
        model = Ingredient
        fields = ["branch", "name", "unit", "reorder_level", "is_active"]

    def __init__(self, *args, tenant=None, membership=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.tenant = tenant
        self.membership = membership
        self.fields["branch"].queryset = self._allowed_branches()
        if membership and membership.primary_branch_id:
            self.fields["branch"].initial = membership.primary_branch_id
        self._apply_bootstrap_classes()

    def _allowed_branches(self):
        if not self.tenant:
            return Branch.objects.none()
        branches = Branch.objects.filter(tenant=self.tenant, is_active=True)
        if (
            self.membership
            and self.membership.role_name in BRANCH_SCOPED_ROLES
            and self.membership.primary_branch_id
        ):
            branches = branches.filter(id=self.membership.primary_branch_id)
        return branches

    def clean_branch(self):
        branch = self.cleaned_data["branch"]
        if self.tenant and branch and branch.tenant_id != self.tenant.id:
            raise forms.ValidationError("Invalid branch for this tenant.")
        return branch

    def _apply_bootstrap_classes(self):
        for _, field in self.fields.items():
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs.setdefault("class", "form-check-input")
            elif isinstance(field.widget, forms.Select):
                field.widget.attrs.setdefault("class", "form-select")
            else:
                field.widget.attrs.setdefault("class", "form-control")


class StockEntryForm(forms.Form):
    branch = forms.ModelChoiceField(queryset=Branch.objects.none())
    ingredient = forms.ModelChoiceField(queryset=Ingredient.objects.none())
    movement_type = forms.ChoiceField(choices=StockEntry.MOVEMENT_CHOICES)
    quantity = forms.DecimalField(min_value=0.001, decimal_places=3, max_digits=14)
    reference = forms.CharField(required=False, max_length=128)
    note = forms.CharField(required=False, max_length=255)

    def __init__(self, *args, tenant=None, membership=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.tenant = tenant
        self.membership = membership

        branches = Branch.objects.none()
        ingredients = Ingredient.objects.none()
        if tenant:
            branches = Branch.objects.filter(tenant=tenant, is_active=True)
            ingredients = Ingredient.objects.filter(tenant=tenant, is_active=True)

            if membership and membership.role_name in BRANCH_SCOPED_ROLES and membership.primary_branch_id:
                branches = branches.filter(id=membership.primary_branch_id)
                ingredients = ingredients.filter(branch_id=membership.primary_branch_id)

        self.fields["branch"].queryset = branches
        self.fields["ingredient"].queryset = ingredients.select_related("branch")

        if membership and membership.primary_branch_id:
            self.fields["branch"].initial = membership.primary_branch_id
        self._apply_bootstrap_classes()

    def clean(self):
        cleaned = super().clean()
        branch = cleaned.get("branch")
        ingredient = cleaned.get("ingredient")
        if branch and ingredient and ingredient.branch_id != branch.id:
            self.add_error("ingredient", "Ingredient does not belong to selected branch.")
        return cleaned

    def _apply_bootstrap_classes(self):
        for _, field in self.fields.items():
            if isinstance(field.widget, forms.Select):
                field.widget.attrs.setdefault("class", "form-select")
            else:
                field.widget.attrs.setdefault("class", "form-control")
