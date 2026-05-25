from django.urls import path

from core.views import (
    AppDashboardView,
    BranchSwitchView,
    CMSPageDetailView,
    ContactRequestView,
    DemoRequestView,
    HealthCheckView,
    ManifestView,
    OfflineFallbackView,
    OperationsResourcesView,
    PublicFaqView,
    PublicFeaturesView,
    PublicHomeView,
    PublicProductView,
    PublicPricingView,
    PublicReportsView,
    PublicSupportView,
    ServiceWorkerView,
    TrialRequestView,
)

app_name = "core"

urlpatterns = [
    path("", PublicHomeView.as_view(), name="home"),
    path("features/", PublicFeaturesView.as_view(), name="features"),
    path("product/", PublicProductView.as_view(), name="product"),
    path("insights/", PublicReportsView.as_view(), name="reports-overview"),
    path("pricing/", PublicPricingView.as_view(), name="pricing"),
    path("support/", PublicSupportView.as_view(), name="support"),
    path("faq/", PublicFaqView.as_view(), name="faq"),
    path("contact/", ContactRequestView.as_view(), name="contact"),
    path("request-demo/", DemoRequestView.as_view(), name="request-demo"),
    path("request-trial/", TrialRequestView.as_view(), name="request-trial"),
    path("pages/<slug:slug>/", CMSPageDetailView.as_view(), name="page-detail"),
    path("dashboard/", AppDashboardView.as_view(), name="dashboard"),
    path("branch/switch/", BranchSwitchView.as_view(), name="branch-switch"),
    path("operations/", OperationsResourcesView.as_view(), name="operations-resources"),
    path("health/", HealthCheckView.as_view(), name="health"),
    path("manifest.webmanifest", ManifestView.as_view(), name="manifest"),
    path("sw.js", ServiceWorkerView.as_view(), name="service-worker"),
    path("offline/", OfflineFallbackView.as_view(), name="offline"),
]
