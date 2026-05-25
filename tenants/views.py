from __future__ import annotations

from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Sum
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views import View
from django.views.generic import FormView, ListView, TemplateView

from audit.models import AuditLog
from backup.models import BackupRecord
from core.models import CMSPage, FeaturesPageContent, HomePageContent, PricingPageContent
from menu.models import Product
from orders.models import Order, PaymentReview
from reports.services import ReportService
from restaurants.models import Branch
from subscriptions.models import Subscription, SubscriptionPlan
from support.models import SupportTicket
from tenants.decorators import system_role_required
from tenants.forms import TenantCreateForm
from tenants.models import Tenant
from tenants.services import TenantProvisioningService


def _is_ar(request) -> bool:
    return (getattr(request, "LANGUAGE_CODE", "ar") or "ar").split("-")[0] == "ar"


@method_decorator(system_role_required, name="dispatch")
class SystemDashboardView(LoginRequiredMixin, TemplateView):
    template_name = "system/dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        is_ar = _is_ar(self.request)
        today = timezone.localdate()
        next_week = today + timedelta(days=7)

        context["tenant_count"] = Tenant.objects.count()
        context["active_tenant_count"] = Tenant.objects.filter(is_active=True).count()
        context["inactive_tenant_count"] = Tenant.objects.filter(is_active=False).count()

        active_subscriptions_qs = Subscription.objects.filter(is_active=True, end_date__gte=today)
        grace_subscriptions_qs = Subscription.objects.filter(end_date__lt=today, grace_period_end__gte=today)
        expired_subscriptions_qs = Subscription.objects.filter(grace_period_end__lt=today)

        context["active_subscriptions"] = active_subscriptions_qs.count()
        context["grace_subscriptions"] = grace_subscriptions_qs.count()
        context["expired_subscriptions"] = expired_subscriptions_qs.count()
        context["expiring_soon_count"] = active_subscriptions_qs.filter(end_date__lte=next_week).count()

        context["audit_count"] = AuditLog.objects.count()
        context["cms_pages"] = CMSPage.objects.count()
        context["marketing_content_entries"] = (
            HomePageContent.objects.count()
            + FeaturesPageContent.objects.count()
            + PricingPageContent.objects.count()
        )
        context["pending_payment_reviews"] = PaymentReview.objects.filter(status=PaymentReview.STATUS_PENDING).count()

        last_day = timezone.now() - timedelta(days=1)
        context["backup_success_24h"] = BackupRecord.objects.filter(
            status=BackupRecord.STATUS_SUCCESS,
            created_at__gte=last_day,
        ).count()
        context["backup_failed_24h"] = BackupRecord.objects.filter(
            status=BackupRecord.STATUS_FAILED,
            created_at__gte=last_day,
        ).count()
        context["support_open_count"] = SupportTicket.objects.filter(status=SupportTicket.STATUS_OPEN).count()

        context["platform_daily_sales"] = (
            Order.objects.filter(status=Order.STATUS_CONFIRMED, created_at__date=today).aggregate(total=Sum("total_amount"))[
                "total"
            ]
            or 0
        )
        context["platform_monthly_sales"] = (
            Order.objects.filter(
                status=Order.STATUS_CONFIRMED,
                created_at__year=today.year,
                created_at__month=today.month,
            ).aggregate(total=Sum("total_amount"))["total"]
            or 0
        )

        context["recent_tenants"] = Tenant.objects.order_by("-created_at")[:6]
        context["expiring_subscriptions"] = (
            Subscription.objects.select_related("tenant", "plan").filter(end_date__gte=today).order_by("end_date")[:10]
        )
        context["expired_subscriptions_list"] = (
            Subscription.objects.select_related("tenant", "plan").filter(grace_period_end__lt=today).order_by("-grace_period_end")[:6]
        )
        context["failed_backups"] = BackupRecord.objects.filter(status=BackupRecord.STATUS_FAILED).order_by("-created_at")[:6]
        context["pending_payment_reviews_list"] = (
            PaymentReview.objects.filter(status=PaymentReview.STATUS_PENDING).select_related("payment", "payment__order")[:6]
        )
        context["recent_support_tickets"] = SupportTicket.objects.select_related("tenant").order_by("-created_at")[:6]
        context["top_tenants_by_sales"] = (
            Tenant.objects.filter(orders_orders__status=Order.STATUS_CONFIRMED)
            .annotate(total_sales=Sum("orders_orders__total_amount"))
            .order_by("-total_sales")[:8]
        )
        context["recent_audit_logs"] = AuditLog.objects.select_related("tenant", "user").order_by("-timestamp")[:10]
        context["slider_admin_url"] = reverse("admin:core_marketingslide_changelist")

        tasks = []
        if context["expiring_soon_count"]:
            tasks.append(
                {
                    "ar": f"{context['expiring_soon_count']} اشتراك ينتهي خلال 7 أيام",
                    "en": f"{context['expiring_soon_count']} subscriptions expiring within 7 days",
                }
            )
        if context["expired_subscriptions"]:
            tasks.append(
                {
                    "ar": "يوجد اشتراكات منتهية تحتاج متابعة تجديد",
                    "en": "Expired subscriptions require renewal follow-up",
                }
            )
        if context["backup_failed_24h"]:
            tasks.append(
                {
                    "ar": "فشل في النسخ الاحتياطي خلال آخر 24 ساعة",
                    "en": "Backup failures detected in the last 24 hours",
                }
            )
        if context["pending_payment_reviews"]:
            tasks.append(
                {
                    "ar": "مراجعات مدفوعات معلقة تحتاج تدقيق",
                    "en": "Pending payment reviews require verification",
                }
            )
        if context["support_open_count"]:
            tasks.append(
                {
                    "ar": "تذاكر دعم مفتوحة تحتاج توزيع",
                    "en": "Open support tickets need assignment",
                }
            )
        context["system_tasks"] = tasks

        active_system_tenant_id = self.request.session.get("system_active_tenant_id")
        context["active_system_tenant"] = None
        if active_system_tenant_id:
            context["active_system_tenant"] = Tenant.objects.filter(id=active_system_tenant_id).first()
        return context


@method_decorator(system_role_required, name="dispatch")
class TenantListView(LoginRequiredMixin, ListView):
    model = Tenant
    template_name = "system/tenants.html"
    context_object_name = "tenants"
    paginate_by = 30

    def get_queryset(self):
        return Tenant.objects.prefetch_related("domains").select_related("subscription__plan")


@method_decorator(system_role_required, name="dispatch")
class TenantDetailView(LoginRequiredMixin, TemplateView):
    template_name = "system/tenant_detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        tenant = get_object_or_404(Tenant, slug=self.kwargs["slug"])
        context["tenant_obj"] = tenant
        context["branches"] = Branch.objects.filter(tenant=tenant).order_by("name")
        context["subscription"] = getattr(tenant, "subscription", None)
        context["daily_sales"] = ReportService.daily_sales(tenant=tenant)
        context["monthly_sales"] = ReportService.monthly_sales(tenant=tenant)
        context["orders_count"] = Order.objects.filter(tenant=tenant).count()
        context["products_count"] = Product.objects.filter(tenant=tenant, is_active=True).count()
        context["pending_reviews"] = PaymentReview.objects.filter(
            tenant=tenant,
            status=PaymentReview.STATUS_PENDING,
        ).count()
        context["recent_orders"] = Order.objects.filter(tenant=tenant).select_related("branch").order_by("-created_at")[:15]
        context["tenant_audit_logs"] = AuditLog.objects.filter(tenant=tenant).select_related("user").order_by("-timestamp")[:15]
        return context


@method_decorator(system_role_required, name="dispatch")
class TenantSwitchView(LoginRequiredMixin, View):
    def post(self, request, slug: str):
        tenant = get_object_or_404(Tenant, slug=slug, is_active=True)
        request.session["system_active_tenant_id"] = tenant.id
        messages.success(
            request,
            f"تم تفعيل سياق المطعم '{tenant.name}' داخل مساحة العمل."
            if _is_ar(request)
            else f"Tenant context '{tenant.name}' is now active in workspace.",
        )
        return redirect("core:dashboard")


@method_decorator(system_role_required, name="dispatch")
class TenantSwitchExitView(LoginRequiredMixin, View):
    def post(self, request):
        request.session.pop("system_active_tenant_id", None)
        messages.success(
            request,
            "تم الرجوع إلى وضع مدير السيستم العام."
            if _is_ar(request)
            else "Returned to global system-admin mode.",
        )
        return redirect("system:dashboard")


@method_decorator(system_role_required, name="dispatch")
class SiteContentManageView(LoginRequiredMixin, TemplateView):
    template_name = "system/site_content.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        home_ar, _ = HomePageContent.objects.get_or_create(language="ar")
        home_en, _ = HomePageContent.objects.get_or_create(language="en")
        features_ar, _ = FeaturesPageContent.objects.get_or_create(language="ar")
        features_en, _ = FeaturesPageContent.objects.get_or_create(language="en")
        pricing_ar, _ = PricingPageContent.objects.get_or_create(language="ar")
        pricing_en, _ = PricingPageContent.objects.get_or_create(language="en")

        context["marketing_models"] = [
            {
                "label": "محتوى الصفحة الرئيسية" if is_ar else "Home Page Content",
                "records": [
                    {"language": "ar", "edit_url": reverse("admin:core_homepagecontent_change", args=[home_ar.id])},
                    {"language": "en", "edit_url": reverse("admin:core_homepagecontent_change", args=[home_en.id])},
                ],
                "list_url": reverse("admin:core_homepagecontent_changelist"),
            },
            {
                "label": "محتوى صفحة الحلول" if is_ar else "Features Page Content",
                "records": [
                    {"language": "ar", "edit_url": reverse("admin:core_featurespagecontent_change", args=[features_ar.id])},
                    {"language": "en", "edit_url": reverse("admin:core_featurespagecontent_change", args=[features_en.id])},
                ],
                "list_url": reverse("admin:core_featurespagecontent_changelist"),
            },
            {
                "label": "محتوى صفحة الباقات" if is_ar else "Pricing Page Content",
                "records": [
                    {"language": "ar", "edit_url": reverse("admin:core_pricingpagecontent_change", args=[pricing_ar.id])},
                    {"language": "en", "edit_url": reverse("admin:core_pricingpagecontent_change", args=[pricing_en.id])},
                ],
                "list_url": reverse("admin:core_pricingpagecontent_changelist"),
            },
            {
                "label": "شرائح السلايدر" if is_ar else "Homepage Slider",
                "records": [
                    {
                        "language": "ar" if is_ar else "en",
                        "edit_url": reverse("admin:core_marketingslide_changelist"),
                    },
                ],
                "list_url": reverse("admin:core_marketingslide_changelist"),
            },
        ]

        context["cms_pages"] = [
            {
                "title": page.title,
                "slug": page.slug,
                "is_published": page.is_published,
                "edit_url": reverse("admin:core_cmspage_change", args=[page.id]),
            }
            for page in CMSPage.objects.all().order_by("title")
        ]
        context["cms_add_url"] = reverse("admin:core_cmspage_add")
        return context


@method_decorator(system_role_required, name="dispatch")
class TenantCreateView(LoginRequiredMixin, FormView):
    template_name = "system/tenant_create.html"
    form_class = TenantCreateForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["language"] = (getattr(self.request, "LANGUAGE_CODE", "ar") or "ar").split("-")[0]
        return kwargs

    def form_valid(self, form):
        tenant = TenantProvisioningService.create_tenant_with_owner(
            data=form.cleaned_data,
            actor=self.request.user,
        )
        language = (getattr(self.request, "LANGUAGE_CODE", "ar") or "ar").split("-")[0]
        if language == "ar":
            message = (
                f"تم إنشاء المطعم '{tenant.name}' بنجاح مع حساب المالك "
                f"'{form.cleaned_data['owner_username']}'."
            )
        else:
            message = (
                f"Restaurant '{tenant.name}' created successfully with owner "
                f"'{form.cleaned_data['owner_username']}'."
            )
        messages.success(self.request, message)
        return redirect("system:tenants")


@method_decorator(system_role_required, name="dispatch")
class PlanListView(LoginRequiredMixin, ListView):
    model = SubscriptionPlan
    template_name = "system/plans.html"
    context_object_name = "plans"


@method_decorator(system_role_required, name="dispatch")
class SubscriptionListView(LoginRequiredMixin, ListView):
    model = Subscription
    template_name = "system/subscriptions.html"
    context_object_name = "subscriptions"
    paginate_by = 50

    def get_queryset(self):
        return Subscription.objects.select_related("tenant", "plan").order_by("end_date")


@method_decorator(system_role_required, name="dispatch")
class AuditLogListView(LoginRequiredMixin, ListView):
    model = AuditLog
    template_name = "system/audit_logs.html"
    context_object_name = "logs"
    paginate_by = 50

    def get_queryset(self):
        return AuditLog.objects.select_related("tenant", "user", "branch")
