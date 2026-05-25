from __future__ import annotations

import json

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.template.response import TemplateResponse
from django.utils import timezone
from django.utils.translation import get_language
from django.views import View
from django.views.generic import FormView, TemplateView

from core.forms import LeadRequestForm
from core.models import CMSPage, LeadRequest
from core.constants import BRANCH_SCOPED_ROLES
from core.policies import AccessPolicy
from core.services import get_marketing_content, get_marketing_slides
from core.utils import safe_redirect_target
from hr.models import Employee
from inventory.models import Ingredient, LowStockAlert, StockEntry
from orders.models import Order
from reports.services import ReportService
from subscriptions.models import SubscriptionPlan


class PublicHomeView(TemplateView):
    template_name = "core/landing.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["plans"] = SubscriptionPlan.objects.order_by("price_egp")
        context["pages"] = CMSPage.objects.filter(is_published=True).order_by("title")
        content = get_marketing_content(get_language() or "ar")
        context["page_content"] = content["home"]
        context["slides"] = get_marketing_slides(get_language() or "ar", fallback=content["home"])
        return context


class PublicFeaturesView(TemplateView):
    template_name = "core/features.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        content = get_marketing_content(get_language() or "ar")
        context["page_content"] = content["features"]
        return context


class PublicPricingView(TemplateView):
    template_name = "core/pricing.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["plans"] = SubscriptionPlan.objects.order_by("price_egp")
        content = get_marketing_content(get_language() or "ar")
        context["page_content"] = content["pricing"]
        return context


class PublicProductView(TemplateView):
    template_name = "core/product.html"


class PublicReportsView(TemplateView):
    template_name = "core/reports_overview.html"


class PublicSupportView(TemplateView):
    template_name = "core/support.html"


class PublicFaqView(TemplateView):
    template_name = "core/faq.html"


class LeadRequestView(FormView):
    template_name = "core/lead_request.html"
    form_class = LeadRequestForm
    request_type = LeadRequest.TYPE_DEMO
    page_title_ar = "احجز عرضاً توضيحياً"
    page_title_en = "Request a Live Demo"
    page_subtitle_ar = "اترك بياناتك وسيتواصل معك فريقنا لترتيب عرض مخصص."
    page_subtitle_en = "Share your details and our team will schedule a tailored walkthrough."

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["language"] = (get_language() or "ar").split("-")[0]
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        lang = (get_language() or "ar").split("-")[0]
        is_ar = lang.startswith("ar")
        context["page_title"] = self.page_title_ar if is_ar else self.page_title_en
        context["page_subtitle"] = self.page_subtitle_ar if is_ar else self.page_subtitle_en
        context["request_type"] = self.request_type
        return context

    def form_valid(self, form):
        lead = form.save(commit=False)
        lead.request_type = self.request_type
        lead.source_page = self.request.path
        lead.save()
        lang = (get_language() or "ar").split("-")[0]
        if lang.startswith("ar"):
            messages.success(self.request, "تم إرسال طلبك بنجاح، سنعود إليك قريباً.")
        else:
            messages.success(self.request, "Your request was submitted successfully. We'll reach out soon.")
        return redirect(self.request.path)


class DemoRequestView(LeadRequestView):
    request_type = LeadRequest.TYPE_DEMO
    page_title_ar = "احجز عرضاً توضيحياً"
    page_title_en = "Request a Live Demo"
    page_subtitle_ar = "استعراض مباشر للنظام مع أحد خبرائنا."
    page_subtitle_en = "A live walkthrough with one of our product experts."


class TrialRequestView(LeadRequestView):
    request_type = LeadRequest.TYPE_TRIAL
    page_title_ar = "ابدأ تجربة مجانية"
    page_title_en = "Start a Free Trial"
    page_subtitle_ar = "نجهز لك تجربة عملية بكامل المزايا."
    page_subtitle_en = "We will set up a full-featured trial for you."


class ContactRequestView(LeadRequestView):
    request_type = LeadRequest.TYPE_CONTACT
    page_title_ar = "تواصل معنا"
    page_title_en = "Contact Us"
    page_subtitle_ar = "أرسل استفسارك وسنرد خلال وقت قصير."
    page_subtitle_en = "Send your inquiry and we will respond shortly."


class CMSPageDetailView(TemplateView):
    template_name = "core/page_detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        page = get_object_or_404(CMSPage, slug=self.kwargs["slug"], is_published=True)
        context["page"] = page
        return context


class AppDashboardView(LoginRequiredMixin, TemplateView):
    template_name = "core/dashboard.html"

    def dispatch(self, request, *args, **kwargs):
        tenant = getattr(request, "tenant", None)
        if tenant:
            return super().dispatch(request, *args, **kwargs)
        if AccessPolicy.is_system_user(request.user):
            return redirect("system:dashboard")
        return redirect("accounts:login")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        tenant = getattr(self.request, "tenant", None)
        membership = getattr(self.request, "membership", None)
        branch = (
            membership.primary_branch
            if membership and membership.primary_branch_id and membership.role_name in BRANCH_SCOPED_ROLES
            else None
        )

        if not tenant:
            context.update(
                {
                    "summary_monthly": {"sales": 0, "expenses": 0, "net_profit": 0},
                    "summary_weekly": {"sales": 0, "expenses": 0, "net_profit": 0},
                    "best": None,
                    "least": None,
                    "active_orders_count": 0,
                    "branch_breakdown": [],
                }
            )
            return context

        summary_monthly = ReportService.period_summary(tenant=tenant, branch=branch, period="monthly")
        summary_weekly = ReportService.period_summary(tenant=tenant, branch=branch, period="weekly")
        context["summary_monthly"] = summary_monthly
        context["summary_weekly"] = summary_weekly
        context.update(ReportService.best_and_least_selling(tenant=tenant, branch=branch))
        active_orders_qs = Order.objects.filter(tenant=tenant, kitchen_status__in=[Order.KITCHEN_PENDING, Order.KITCHEN_PREPARING])
        if branch:
            active_orders_qs = active_orders_qs.filter(branch=branch)
        context["active_orders_count"] = active_orders_qs.count()
        branch_breakdown = ReportService.branch_financial_breakdown(tenant=tenant, period="monthly")
        context["branch_breakdown"] = branch_breakdown
        context["branch_breakdown_json"] = json.dumps(
            [
                {
                    "name": row["branch"].name,
                    "sales": float(row["sales"] or 0),
                    "expenses": float(row["expenses"] or 0),
                }
                for row in branch_breakdown
            ]
        )
        return context


class BranchSwitchView(LoginRequiredMixin, View):
    def post(self, request: HttpRequest) -> HttpResponse:
        tenant = getattr(request, "tenant", None)
        fallback = reverse("core:dashboard")
        next_url = safe_redirect_target(request, request.POST.get("next") or request.META.get("HTTP_REFERER"), fallback)
        if not tenant:
            return redirect(next_url)

        membership = getattr(request, "membership", None)
        requested_branch_id = request.POST.get("branch_id")
        if membership and membership.role_name in BRANCH_SCOPED_ROLES and membership.primary_branch_id:
            request.session["active_branch_id"] = membership.primary_branch_id
            return redirect(next_url)

        allowed = AccessPolicy.permitted_branches(request, tenant=tenant)
        branch = None
        if requested_branch_id:
            branch = allowed.filter(id=requested_branch_id).first()
        if not branch:
            branch = allowed.first()
        if branch:
            request.session["active_branch_id"] = branch.id
        return redirect(next_url)


class OperationsResourcesView(LoginRequiredMixin, TemplateView):
    template_name = "core/operations_resources.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        tenant = getattr(self.request, "tenant", None)
        membership = getattr(self.request, "membership", None)
        context.update(
            {
                "ingredients_count": 0,
                "low_stock_count": 0,
                "stock_entries_count": 0,
                "employees_count": 0,
                "recent_entries": [],
            }
        )
        if not tenant:
            return context

        ingredients = Ingredient.objects.filter(tenant=tenant)
        alerts = LowStockAlert.objects.filter(tenant=tenant, status=LowStockAlert.STATUS_OPEN)
        entries = StockEntry.objects.filter(tenant=tenant).select_related("ingredient", "branch")
        employees = Employee.objects.filter(tenant=tenant)
        if membership and membership.role_name in BRANCH_SCOPED_ROLES and membership.primary_branch_id:
            ingredients = ingredients.filter(branch_id=membership.primary_branch_id)
            alerts = alerts.filter(branch_id=membership.primary_branch_id)
            entries = entries.filter(branch_id=membership.primary_branch_id)
            employees = employees.filter(branch_id=membership.primary_branch_id)

        context["ingredients_count"] = ingredients.count()
        context["low_stock_count"] = alerts.count()
        context["stock_entries_count"] = entries.count()
        context["employees_count"] = employees.count()
        context["recent_entries"] = entries.order_by("-created_at")[:8]
        return context


class OfflineFallbackView(TemplateView):
    template_name = "pos/offline.html"


class ServiceWorkerView(View):
    def get(self, request: HttpRequest) -> HttpResponse:
        response = TemplateResponse(request, "core/sw.js", {})
        response["Content-Type"] = "application/javascript"
        response["Service-Worker-Allowed"] = "/"
        return response


class ManifestView(View):
    def get(self, request: HttpRequest) -> JsonResponse:
        return JsonResponse(
            {
                "name": "Restoraq POS",
                "short_name": "Restoraq",
                "start_url": "/pos/",
                "display": "standalone",
                "background_color": "#f6f8fb",
                "theme_color": "#4e73df",
                "lang": "ar",
                "icons": [
                    {
                        "src": "/static/icons/icon-192.png",
                        "sizes": "192x192",
                        "type": "image/png",
                    },
                    {
                        "src": "/static/icons/icon-512.png",
                        "sizes": "512x512",
                        "type": "image/png",
                    },
                ],
            }
        )


class HealthCheckView(View):
    def get(self, request: HttpRequest) -> JsonResponse:
        return JsonResponse({"status": "ok", "time": timezone.now().isoformat()})


def custom_404(request, exception):
    context = {
        "active_language": (get_language() or "ar").split("-")[0],
        "text_direction": "rtl" if (get_language() or "ar").startswith("ar") else "ltr",
    }
    return TemplateResponse(request, "404.html", context, status=404)


def hidden_entry(request):
    context = {
        "active_language": (get_language() or "ar").split("-")[0],
        "text_direction": "rtl" if (get_language() or "ar").startswith("ar") else "ltr",
    }
    return TemplateResponse(request, "404.html", context, status=404)
