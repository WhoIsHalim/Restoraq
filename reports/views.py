from __future__ import annotations

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.views import View
from django.views.generic import TemplateView

from core.constants import BRANCH_SCOPED_ROLES
from core.policies import AccessPolicy
from featureflags.services import FeatureService
from reports.services import ReportService
from restaurants.models import Branch


ALLOWED_PERIODS = {"daily", "weekly", "biweekly", "monthly", "quarterly", "yearly"}


class ReportsDashboardView(LoginRequiredMixin, TemplateView):
    template_name = "reports/dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        ctx = AccessPolicy.context(self.request)
        tenant = ctx.tenant
        membership = ctx.membership
        branch = (
            membership.primary_branch
            if membership and membership.primary_branch_id and membership.role_name in BRANCH_SCOPED_ROLES
            else None
        )
        requested_branch_id = self.request.GET.get("branch_id")
        if tenant and requested_branch_id and (not membership or membership.role_name not in BRANCH_SCOPED_ROLES):
            branch = Branch.objects.filter(tenant=tenant, id=requested_branch_id, is_active=True).first()

        period = self.request.GET.get("period", "monthly")
        if period not in ALLOWED_PERIODS:
            period = "monthly"

        context["period"] = period
        context["selected_branch_id"] = str(getattr(branch, "id", "") or "")
        context["branch_options"] = Branch.objects.filter(tenant=tenant, is_active=True).order_by("name") if tenant else []
        context["period_choices"] = [
            ("daily", "يومي" if self.request.LANGUAGE_CODE.startswith("ar") else "Daily"),
            ("weekly", "أسبوعي" if self.request.LANGUAGE_CODE.startswith("ar") else "Weekly"),
            ("biweekly", "كل أسبوعين" if self.request.LANGUAGE_CODE.startswith("ar") else "Biweekly"),
            ("monthly", "شهري" if self.request.LANGUAGE_CODE.startswith("ar") else "Monthly"),
            ("quarterly", "ربع سنوي" if self.request.LANGUAGE_CODE.startswith("ar") else "Quarterly"),
            ("yearly", "سنوي" if self.request.LANGUAGE_CODE.startswith("ar") else "Yearly"),
        ]

        if tenant:
            summary = ReportService.period_summary(tenant=tenant, branch=branch, period=period)
            context.update(summary)
            context.update(ReportService.best_and_least_selling(tenant=tenant, branch=branch))
            context["branch_breakdown"] = ReportService.branch_financial_breakdown(tenant=tenant, period=period)
        else:
            context.update(
                {
                    "sales": 0,
                    "expenses": 0,
                    "net_profit": 0,
                    "best": None,
                    "least": None,
                    "branch_breakdown": [],
                }
            )
        return context


class ReportsAdvancedAPIView(LoginRequiredMixin, View):
    def get(self, request):
        ctx = AccessPolicy.context(request)
        tenant = ctx.tenant
        membership = ctx.membership
        branch = (
            membership.primary_branch
            if membership and membership.primary_branch_id and membership.role_name in BRANCH_SCOPED_ROLES
            else None
        )
        requested_branch_id = request.GET.get("branch_id")
        if tenant and requested_branch_id and (not membership or membership.role_name not in BRANCH_SCOPED_ROLES):
            branch = Branch.objects.filter(tenant=tenant, id=requested_branch_id, is_active=True).first()
        period = request.GET.get("period", "monthly")
        if period not in ALLOWED_PERIODS:
            period = "monthly"

        if not tenant:
            return JsonResponse({"labels": [], "datasets": []})

        series = ReportService.sales_vs_expense_series(tenant=tenant, branch=branch, period=period)
        language = (getattr(request, "LANGUAGE_CODE", "ar") or "ar").split("-")[0]
        sales_label = "المبيعات" if language == "ar" else "Sales"
        expenses_label = "المصروفات" if language == "ar" else "Expenses"

        return JsonResponse(
            {
                "labels": series["labels"],
                "datasets": [
                    {
                        "type": "line",
                        "label": sales_label,
                        "data": series["sales"],
                        "borderColor": "#1e4db7",
                        "backgroundColor": "rgba(30, 77, 183, 0.18)",
                        "fill": True,
                        "tension": 0.32,
                    },
                    {
                        "type": "bar",
                        "label": expenses_label,
                        "data": series["expenses"],
                        "backgroundColor": "rgba(220, 78, 78, 0.45)",
                    },
                ],
            }
        )


class ReportsAnalyticsAPIView(LoginRequiredMixin, View):
    def get(self, request):
        ctx = AccessPolicy.context(request)
        tenant = ctx.tenant
        membership = ctx.membership
        branch = (
            membership.primary_branch
            if membership and membership.primary_branch_id and membership.role_name in BRANCH_SCOPED_ROLES
            else None
        )
        requested_branch_id = request.GET.get("branch_id")
        if tenant and requested_branch_id and (not membership or membership.role_name not in BRANCH_SCOPED_ROLES):
            branch = Branch.objects.filter(tenant=tenant, id=requested_branch_id, is_active=True).first()
        period = request.GET.get("period", "monthly")
        if period not in ALLOWED_PERIODS:
            period = "monthly"

        if not tenant:
            return JsonResponse(
                {
                    "trend": {"labels": [], "sales": [], "expenses": []},
                    "status": {"draft": 0, "confirmed": 0, "cancelled": 0},
                    "top_products": {"labels": [], "values": []},
                    "branches": {"labels": [], "sales": [], "expenses": [], "net": []},
                }
            )

        trend = ReportService.sales_vs_expense_series(tenant=tenant, branch=branch, period=period)
        status = ReportService.order_status_breakdown(tenant=tenant, branch=branch, period=period)
        top_products = ReportService.top_products_series(tenant=tenant, branch=branch, period=period, limit=7)
        branch_rows = ReportService.branch_financial_breakdown(tenant=tenant, period=period)
        return JsonResponse(
            {
                "trend": trend,
                "status": status,
                "top_products": top_products,
                "branches": {
                    "labels": [row["branch"].name for row in branch_rows],
                    "sales": [float(row["sales"] or 0) for row in branch_rows],
                    "expenses": [float(row["expenses"] or 0) for row in branch_rows],
                    "net": [float(row["net_profit"] or 0) for row in branch_rows],
                },
            }
        )


class AccountingDashboardView(LoginRequiredMixin, TemplateView):
    template_name = "reports/accounting.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        ctx = AccessPolicy.context(self.request)
        tenant = ctx.tenant
        membership = ctx.membership
        branch = (
            membership.primary_branch
            if membership and membership.primary_branch_id and membership.role_name in BRANCH_SCOPED_ROLES
            else None
        )
        requested_branch_id = self.request.GET.get("branch_id")
        if tenant and requested_branch_id and (not membership or membership.role_name not in BRANCH_SCOPED_ROLES):
            branch = Branch.objects.filter(tenant=tenant, id=requested_branch_id, is_active=True).first()

        period = self.request.GET.get("period", "monthly")
        if period not in ALLOWED_PERIODS:
            period = "monthly"
        context["period"] = period
        context["selected_branch_id"] = str(getattr(branch, "id", "") or "")
        context["branch_options"] = Branch.objects.filter(tenant=tenant, is_active=True).order_by("name") if tenant else []

        if not tenant:
            context.update({"sales": 0, "expenses": 0, "net_profit": 0, "branch_breakdown": []})
            return context

        if not FeatureService.is_enabled(tenant, "accounting_module"):
            context["accounting_locked"] = True
            return context

        summary = ReportService.period_summary(tenant=tenant, branch=branch, period=period)
        context.update(summary)
        context["branch_breakdown"] = ReportService.branch_financial_breakdown(tenant=tenant, period=period)
        context["accounting_locked"] = False
        return context


class SalesChartAPIView(LoginRequiredMixin, View):
    def get(self, request):
        # Backward compatibility for existing widgets
        return ReportsAdvancedAPIView().get(request)
