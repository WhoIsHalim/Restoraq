from django.urls import path

from support.views import SupportTicketCreateView, SupportTicketListView, SupportTicketUpdateView

app_name = "support"

urlpatterns = [
    path("", SupportTicketListView.as_view(), name="list"),
    path("new/", SupportTicketCreateView.as_view(), name="create"),
    path("<int:pk>/edit/", SupportTicketUpdateView.as_view(), name="edit"),
]
