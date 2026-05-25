from django.urls import path

from crm.views import CustomerCreateView, CustomerDetailView, CustomerListView, CustomerUpdateView

app_name = "crm"

urlpatterns = [
    path("", CustomerListView.as_view(), name="customers"),
    path("new/", CustomerCreateView.as_view(), name="customer-create"),
    path("<int:pk>/", CustomerDetailView.as_view(), name="customer-detail"),
    path("<int:pk>/edit/", CustomerUpdateView.as_view(), name="customer-edit"),
]
