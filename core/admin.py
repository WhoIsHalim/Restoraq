from django.contrib import admin

from core.models import (
    CMSPage,
    FeaturesPageContent,
    HomePageContent,
    MarketingSlide,
    PricingPageContent,
    LeadRequest,
)

admin.site.site_header = "Restoraq Administration"
admin.site.site_title = "Restoraq Admin"
admin.site.index_title = "Platform Control"
admin.site.enable_nav_sidebar = False


class LanguageAwareAdminMixin:
    ar_labels: dict[str, str] = {}

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        language = (getattr(request, "LANGUAGE_CODE", "en") or "en").split("-")[0]
        if language == "ar":
            for field_name, label in self.ar_labels.items():
                if field_name in form.base_fields:
                    form.base_fields[field_name].label = label
        return form


class RichTextAdminMixin(LanguageAwareAdminMixin):
    rich_text_fields: tuple[str, ...] = ()

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj=obj, **kwargs)
        for field_name in self.rich_text_fields:
            field = form.base_fields.get(field_name)
            if not field:
                continue
            widget = field.widget
            widget.attrs["class"] = f"{widget.attrs.get('class', '')} js-richtext".strip()
        return form


@admin.register(CMSPage)
class CMSPageAdmin(RichTextAdminMixin, admin.ModelAdmin):
    list_display = ("title", "slug", "is_published", "updated_at")
    list_filter = ("is_published",)
    search_fields = ("title", "slug")
    rich_text_fields = ("body",)
    ar_labels = {
        "title": "عنوان الصفحة",
        "slug": "الرابط المختصر (Slug)",
        "body": "المحتوى",
        "is_published": "منشور",
    }


@admin.register(HomePageContent)
class HomePageContentAdmin(RichTextAdminMixin, admin.ModelAdmin):
    list_display = ("language", "title", "updated_at")
    search_fields = ("title", "subtitle", "problem_title")
    rich_text_fields = ("subtitle", "problem_text", "solution_text", "final_text")
    ar_labels = {
        "language": "اللغة",
        "kicker": "الشارة أعلى العنوان",
        "title": "العنوان الرئيسي",
        "subtitle": "العنوان الفرعي",
        "primary_cta": "الزر الرئيسي",
        "secondary_cta": "الزر الثانوي",
        "problem_title": "عنوان المشكلة",
        "problem_text": "نص المشكلة",
        "solution_text": "نص الحل",
        "highlights": "نقاط المميزات",
        "metrics": "نقاط مؤشرات الأداء",
        "final_title": "عنوان الخاتمة",
        "final_text": "نص الخاتمة",
        "final_cta": "زر الخاتمة",
    }


@admin.register(FeaturesPageContent)
class FeaturesPageContentAdmin(RichTextAdminMixin, admin.ModelAdmin):
    list_display = ("language", "title", "updated_at")
    search_fields = ("title", "subtitle", "closing_title")
    rich_text_fields = ("subtitle", "closing_text")
    ar_labels = {
        "language": "اللغة",
        "title": "العنوان الرئيسي",
        "subtitle": "الوصف",
        "cards": "بطاقات الحلول",
        "closing_title": "عنوان الخاتمة",
        "closing_text": "نص الخاتمة",
        "closing_cta": "زر الخاتمة",
    }


@admin.register(PricingPageContent)
class PricingPageContentAdmin(RichTextAdminMixin, admin.ModelAdmin):
    list_display = ("language", "title", "updated_at")
    search_fields = ("title", "subtitle", "closing_cta")
    rich_text_fields = ("subtitle", "money_back", "closing_cta")
    ar_labels = {
        "language": "اللغة",
        "title": "العنوان الرئيسي",
        "subtitle": "الوصف",
        "plan_badges": "شارات الباقات",
        "plan_descriptions": "وصف الباقات",
        "faq_items": "أسئلة شائعة",
        "money_back": "نص ضمان الاسترجاع",
        "closing_cta": "دعوة الإجراء",
    }


@admin.register(MarketingSlide)
class MarketingSlideAdmin(LanguageAwareAdminMixin, admin.ModelAdmin):
    list_display = ("title", "language", "order", "is_active")
    list_filter = ("language", "is_active")
    search_fields = ("title", "subtitle", "cta_text")
    ordering = ("language", "order", "id")
    ar_labels = {
        "language": "اللغة",
        "title": "عنوان الشريحة",
        "subtitle": "وصف مختصر",
        "cta_text": "نص الزر",
        "cta_url": "رابط الزر",
        "image_path": "مسار الصورة",
        "order": "الترتيب",
        "is_active": "مفعلة",
    }


@admin.register(LeadRequest)
class LeadRequestAdmin(LanguageAwareAdminMixin, admin.ModelAdmin):
    list_display = ("name", "request_type", "inquiry_category", "status", "phone", "email", "created_at")
    list_filter = ("request_type", "inquiry_category", "status", "contact_method")
    search_fields = ("name", "email", "phone", "company", "message")
    readonly_fields = ("created_at", "updated_at")
    ar_labels = {
        "name": "الاسم",
        "email": "البريد الإلكتروني",
        "phone": "الهاتف",
        "company": "اسم المطعم/الشركة",
        "request_type": "نوع الطلب",
        "inquiry_category": "نوع الاستفسار",
        "contact_method": "طريقة التواصل",
        "preferred_time": "وقت التواصل المفضل",
        "status": "الحالة",
        "message": "الرسالة",
        "source_page": "صفحة المصدر",
    }
