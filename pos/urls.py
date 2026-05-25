from django.urls import path

from pos.views import (
    POSCustomerLookupAPIView,
    POSMenuPayloadAPIView,
    POSOrderPreviewAPIView,
    POSOrderStatusAPIView,
    POSSyncOrdersAPIView,
    POSSyncStatusFragmentView,
    POSTerminalView,
)

app_name = "pos"

urlpatterns = [
    path("", POSTerminalView.as_view(), name="terminal"),
    path("sync-status/", POSSyncStatusFragmentView.as_view(), name="sync-status"),
    path("api/menu/", POSMenuPayloadAPIView.as_view(), name="menu-payload"),
    path("api/customers/", POSCustomerLookupAPIView.as_view(), name="customer-lookup"),
    path("api/order/preview/", POSOrderPreviewAPIView.as_view(), name="order-preview"),
    path("api/sync-orders/", POSSyncOrdersAPIView.as_view(), name="sync-orders"),
    path("api/order/<int:order_id>/status/", POSOrderStatusAPIView.as_view(), name="order-status"),
]
