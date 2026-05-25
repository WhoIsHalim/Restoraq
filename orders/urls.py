from django.urls import path

from orders.views import (
    KitchenBoardView,
    KitchenStatusUpdateView,
    OrderDetailView,
    OrderCreateAPIView,
    OrderReopenView,
    OrderListView,
    OrderUpdateView,
    PaymentReviewQueueAPIView,
)

app_name = "orders"

urlpatterns = [
    path("", OrderListView.as_view(), name="list"),
    path("<int:pk>/", OrderDetailView.as_view(), name="detail"),
    path("<int:pk>/edit/", OrderUpdateView.as_view(), name="edit"),
    path("<int:pk>/reopen/", OrderReopenView.as_view(), name="reopen"),
    path("kitchen/", KitchenBoardView.as_view(), name="kitchen-board"),
    path("kitchen/<int:order_id>/status/", KitchenStatusUpdateView.as_view(), name="kitchen-status"),
    path("api/create/", OrderCreateAPIView.as_view(), name="create"),
    path("api/payment-reviews/", PaymentReviewQueueAPIView.as_view(), name="payment-reviews"),
]
