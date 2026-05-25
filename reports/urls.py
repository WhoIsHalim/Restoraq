from django.urls import path

from reports.views import (
    AccountingDashboardView,
    ReportsAdvancedAPIView,
    ReportsAnalyticsAPIView,
    ReportsDashboardView,
    SalesChartAPIView,
)

app_name = "reports"

urlpatterns = [
    path("", ReportsDashboardView.as_view(), name="dashboard"),
    path("accounting/", AccountingDashboardView.as_view(), name="accounting"),
    path("api/advanced/", ReportsAdvancedAPIView.as_view(), name="advanced"),
    path("api/analytics/", ReportsAnalyticsAPIView.as_view(), name="analytics"),
    path("api/sales-chart/", SalesChartAPIView.as_view(), name="sales-chart"),
]
