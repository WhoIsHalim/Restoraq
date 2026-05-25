from django.urls import path

from restaurants.views import (
    BranchCreateView,
    BranchListView,
    BranchUpdateView,
    DiningTableCreateView,
    DiningTableListView,
    DiningTableUpdateView,
    FloorAreaCreateView,
    FloorAreaListView,
    FloorAreaUpdateView,
    ReservationCreateView,
    ReservationListView,
    ReservationUpdateView,
    RestaurantCreateRedirectView,
)

app_name = "restaurants"

urlpatterns = [
    path("", BranchListView.as_view(), name="branches-root"),
    path("branches/", BranchListView.as_view(), name="branches"),
    path("branches/new/", BranchCreateView.as_view(), name="branch-create"),
    path("branches/<int:pk>/edit/", BranchUpdateView.as_view(), name="branch-edit"),
    path("areas/", FloorAreaListView.as_view(), name="floor-areas"),
    path("areas/new/", FloorAreaCreateView.as_view(), name="floor-area-create"),
    path("areas/<int:pk>/edit/", FloorAreaUpdateView.as_view(), name="floor-area-edit"),
    path("tables/", DiningTableListView.as_view(), name="tables"),
    path("tables/new/", DiningTableCreateView.as_view(), name="table-create"),
    path("tables/<int:pk>/edit/", DiningTableUpdateView.as_view(), name="table-edit"),
    path("reservations/", ReservationListView.as_view(), name="reservations"),
    path("reservations/new/", ReservationCreateView.as_view(), name="reservation-create"),
    path("reservations/<int:pk>/edit/", ReservationUpdateView.as_view(), name="reservation-edit"),
    path("new/", RestaurantCreateRedirectView.as_view(), name="restaurant-create-redirect"),
]
