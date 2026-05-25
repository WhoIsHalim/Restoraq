from django.urls import path

from tenants.views import (
    AuditLogListView,
    PlanListView,
    SiteContentManageView,
    SubscriptionListView,
    TenantSwitchExitView,
    TenantSwitchView,
    TenantDetailView,
    SystemDashboardView,
    TenantCreateView,
    TenantListView,
)
from support.views import SupportTicketCreateView, SupportTicketListView, SupportTicketUpdateView

app_name = "system"

urlpatterns = [
    path("", SystemDashboardView.as_view(), name="dashboard"),
    path("tenants/", TenantListView.as_view(), name="tenants"),
    path("tenants/new/", TenantCreateView.as_view(), name="tenant-create"),
    path("tenant/new/", TenantCreateView.as_view(), name="tenant-create-alias"),
    path("restaurants/new/", TenantCreateView.as_view(), name="restaurant-create-alias"),
    path("tenants/<slug:slug>/", TenantDetailView.as_view(), name="tenant-detail"),
    path("tenants/<slug:slug>/switch/", TenantSwitchView.as_view(), name="tenant-switch"),
    path("tenants/switch/exit/", TenantSwitchExitView.as_view(), name="tenant-switch-exit"),
    path("plans/", PlanListView.as_view(), name="plans"),
    path("subscriptions/", SubscriptionListView.as_view(), name="subscriptions"),
    path("audit-logs/", AuditLogListView.as_view(), name="audit-logs"),
    path("site-content/", SiteContentManageView.as_view(), name="site-content"),
    path("support/", SupportTicketListView.as_view(), name="support-tickets"),
    path("support/new/", SupportTicketCreateView.as_view(), name="support-ticket-create"),
    path("support/<int:pk>/edit/", SupportTicketUpdateView.as_view(), name="support-ticket-edit"),
]
