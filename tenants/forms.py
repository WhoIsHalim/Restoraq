from __future__ import annotations

from datetime import timedelta

from django import forms
from django.contrib.auth import get_user_model
from django.utils import timezone

from subscriptions.models import SubscriptionPlan
from tenants.models import TenantDomain


class TenantCreateForm(forms.Form):
    tenant_name = forms.CharField(max_length=255, label="Restaurant Name")
    tenant_slug = forms.SlugField(
        max_length=64,
        required=False,
        help_text="Optional. Leave empty to auto-generate from restaurant name.",
        label="Restaurant Slug",
    )
    tenant_domain = forms.CharField(
        max_length=255,
        required=False,
        help_text="Optional. Example: acme.example.com",
        label="Primary Domain",
    )
    default_language = forms.ChoiceField(choices=(("ar", "Arabic"), ("en", "English")), initial="ar")
    vat_rate = forms.DecimalField(max_digits=5, decimal_places=2, initial=14, min_value=0)
    tax_inclusive_pricing = forms.BooleanField(required=False, initial=True)

    plan = forms.ModelChoiceField(queryset=SubscriptionPlan.objects.order_by("price_egp"))
    subscription_start_date = forms.DateField(initial=timezone.localdate)
    subscription_end_date = forms.DateField(initial=lambda: timezone.localdate() + timedelta(days=30))
    is_subscription_active = forms.BooleanField(required=False, initial=True)

    branch_name = forms.CharField(max_length=255, initial="Main Branch")
    branch_code = forms.CharField(max_length=32, initial="MAIN")
    branch_address = forms.CharField(widget=forms.Textarea(attrs={"rows": 2}), required=False)
    branch_phone = forms.CharField(max_length=32, required=False)

    owner_username = forms.CharField(max_length=150)
    owner_email = forms.EmailField(required=False)
    owner_phone = forms.CharField(max_length=32, required=False)
    owner_password = forms.CharField(widget=forms.PasswordInput)

    def __init__(self, *args, **kwargs):
        language = kwargs.pop("language", "ar")
        super().__init__(*args, **kwargs)
        self.language = "en" if str(language).startswith("en") else "ar"

        if self.language == "ar":
            labels = {
                "tenant_name": "اسم المطعم",
                "tenant_slug": "Slug المطعم",
                "tenant_domain": "الدومين الرئيسي",
                "default_language": "اللغة الافتراضية",
                "vat_rate": "ضريبة القيمة المضافة %",
                "tax_inclusive_pricing": "الأسعار تشمل الضريبة",
                "plan": "الباقة",
                "subscription_start_date": "بداية الاشتراك",
                "subscription_end_date": "نهاية الاشتراك",
                "is_subscription_active": "الاشتراك نشط",
                "branch_name": "اسم الفرع الرئيسي",
                "branch_code": "كود الفرع",
                "branch_address": "عنوان الفرع",
                "branch_phone": "هاتف الفرع",
                "owner_username": "اسم مستخدم مالك المطعم",
                "owner_email": "بريد المالك",
                "owner_phone": "هاتف المالك",
                "owner_password": "كلمة مرور المالك",
            }
            helps = {
                "tenant_slug": "اختياري. اتركه فارغًا ليتم إنشاؤه تلقائيًا من اسم المطعم.",
                "tenant_domain": "اختياري. مثال: acme.example.com",
            }
            self.fields["branch_name"].initial = "الفرع الرئيسي"
        else:
            labels = {
                "tenant_name": "Restaurant Name",
                "tenant_slug": "Restaurant Slug",
                "tenant_domain": "Primary Domain",
                "default_language": "Default Language",
                "vat_rate": "VAT Rate %",
                "tax_inclusive_pricing": "Tax Inclusive Pricing",
                "plan": "Subscription Plan",
                "subscription_start_date": "Subscription Start Date",
                "subscription_end_date": "Subscription End Date",
                "is_subscription_active": "Subscription Active",
                "branch_name": "Main Branch Name",
                "branch_code": "Branch Code",
                "branch_address": "Branch Address",
                "branch_phone": "Branch Phone",
                "owner_username": "Owner Username",
                "owner_email": "Owner Email",
                "owner_phone": "Owner Phone",
                "owner_password": "Owner Password",
            }
            helps = {
                "tenant_slug": "Optional. Leave empty to auto-generate from restaurant name.",
                "tenant_domain": "Optional. Example: acme.example.com",
            }

        for field_name, label in labels.items():
            self.fields[field_name].label = label
        for field_name, help_text in helps.items():
            self.fields[field_name].help_text = help_text

        if self.language == "ar":
            self.fields["default_language"].choices = (("ar", "العربية"), ("en", "الإنجليزية"))
            plan_map = {
                "basic": "أساسي",
                "standard": "قياسي",
                "multibranch": "متعدد الفروع",
                "pro": "احترافي",
            }

            def plan_label(plan):
                return f"{plan_map.get(plan.code.lower(), plan.name)} - {plan.price_egp} جنيه"

            self.fields["plan"].label_from_instance = plan_label
        else:
            self.fields["default_language"].choices = (("ar", "Arabic"), ("en", "English"))

        for _, field in self.fields.items():
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs.setdefault("class", "form-check-input")
            elif isinstance(field.widget, forms.Textarea):
                field.widget.attrs.setdefault("class", "form-control")
            else:
                css = "form-control"
                if isinstance(field.widget, forms.Select):
                    css = "form-select"
                field.widget.attrs.setdefault("class", css)
            if isinstance(field, forms.DateField):
                field.widget.attrs.setdefault("type", "date")

    def clean_owner_username(self):
        username = self.cleaned_data["owner_username"]
        if get_user_model().objects.filter(username=username).exists():
            if self.language == "ar":
                raise forms.ValidationError("اسم المستخدم موجود بالفعل.")
            raise forms.ValidationError("This username already exists.")
        return username

    def clean_tenant_domain(self):
        domain = (self.cleaned_data.get("tenant_domain") or "").strip().lower()
        if not domain:
            return ""
        if TenantDomain.objects.filter(domain=domain).exists():
            if self.language == "ar":
                raise forms.ValidationError("هذا الدومين مرتبط بمطعم آخر بالفعل.")
            raise forms.ValidationError("This domain is already linked to another tenant.")
        return domain

    def clean(self):
        cleaned = super().clean()
        start_date = cleaned.get("subscription_start_date")
        end_date = cleaned.get("subscription_end_date")
        if start_date and end_date and end_date < start_date:
            if self.language == "ar":
                self.add_error("subscription_end_date", "تاريخ النهاية يجب أن يكون بعد تاريخ البداية.")
            else:
                self.add_error("subscription_end_date", "End date must be after start date.")
        return cleaned
