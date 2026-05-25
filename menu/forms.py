from __future__ import annotations

from django import forms

from core.constants import BRANCH_SCOPED_ROLES
from inventory.models import Ingredient, Recipe
from menu.models import Category, Product
from restaurants.models import Branch


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ["branch", "name", "display_order", "is_active"]

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
            self.fields["name"].label = "اسم التصنيف"
            self.fields["display_order"].label = "ترتيب العرض"
            self.fields["is_active"].label = "التصنيف نشط"
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

    def _apply_bootstrap_classes(self):
        for _, field in self.fields.items():
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs.setdefault("class", "form-check-input")
            elif isinstance(field.widget, forms.Select):
                field.widget.attrs.setdefault("class", "form-select")
            else:
                field.widget.attrs.setdefault("class", "form-control")


class ProductForm(forms.ModelForm):
    apply_to_all_branches = forms.BooleanField(required=False, label="Apply to all branches")

    class Meta:
        model = Product
        fields = [
            "branch",
            "category",
            "name",
            "sku",
            "price",
            "tax_rate",
            "is_tax_inclusive",
            "is_active",
            "image",
        ]

    def __init__(self, *args, tenant=None, membership=None, language: str = "en", **kwargs):
        super().__init__(*args, **kwargs)
        self.tenant = tenant
        self.membership = membership
        self.language = (language or "en").split("-")[0]
        branches = self._allowed_branches()
        self.fields["branch"].queryset = branches
        self.fields["category"].queryset = Category.objects.filter(tenant=tenant).order_by("name")
        if membership and membership.primary_branch_id:
            self.fields["branch"].initial = membership.primary_branch_id
        self.fields["image"].required = False
        if self.language == "ar":
            self.fields["branch"].label = "الفرع"
            self.fields["category"].label = "التصنيف"
            self.fields["name"].label = "اسم الصنف"
            self.fields["sku"].label = "كود الصنف"
            self.fields["price"].label = "السعر"
            self.fields["tax_rate"].label = "الضريبة (%)"
            self.fields["is_tax_inclusive"].label = "السعر شامل الضريبة"
            self.fields["is_active"].label = "الصنف نشط"
            self.fields["image"].label = "صورة الصنف"
            self.fields["apply_to_all_branches"].label = "تطبيق هذا الصنف على كل فروع المطعم"
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

    def clean(self):
        cleaned = super().clean()
        branch = cleaned.get("branch")
        category = cleaned.get("category")
        if category and self.tenant and category.tenant_id != self.tenant.id:
            self.add_error(
                "category",
                "تصنيف غير صالح لهذا المطعم." if self.language == "ar" else "Invalid category for tenant.",
            )
        if cleaned.get("apply_to_all_branches"):
            cleaned["branch"] = None
        if category and branch and category.branch_id != branch.id:
            self.add_error(
                "category",
                "التصنيف لا يتبع الفرع المختار." if self.language == "ar" else "Category does not belong to selected branch.",
            )
        return cleaned

    def _apply_bootstrap_classes(self):
        for _, field in self.fields.items():
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs.setdefault("class", "form-check-input")
            elif isinstance(field.widget, forms.Select):
                field.widget.attrs.setdefault("class", "form-select")
            else:
                field.widget.attrs.setdefault("class", "form-control")


class RecipeForm(forms.ModelForm):
    class Meta:
        model = Recipe
        fields = ["ingredient", "quantity_per_unit"]

    def __init__(self, *args, tenant=None, branch=None, language: str = "en", **kwargs):
        super().__init__(*args, **kwargs)
        self.language = (language or "en").split("-")[0]
        ingredients = Ingredient.objects.none()
        if tenant:
            ingredients = Ingredient.objects.filter(tenant=tenant, is_active=True)
            if branch:
                ingredients = ingredients.filter(branch__in=[branch, None])
        self.fields["ingredient"].queryset = ingredients.order_by("name")
        if self.language == "ar":
            self.fields["ingredient"].label = "المكوّن"
            self.fields["quantity_per_unit"].label = "الكمية لكل وحدة"
        self._apply_bootstrap_classes()

    def _apply_bootstrap_classes(self):
        for _, field in self.fields.items():
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs.setdefault("class", "form-check-input")
            elif isinstance(field.widget, forms.Select):
                field.widget.attrs.setdefault("class", "form-select")
            else:
                field.widget.attrs.setdefault("class", "form-control")
