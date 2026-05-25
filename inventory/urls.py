from django.urls import path

from inventory.views import (
    IngredientCreateView,
    IngredientListView,
    IngredientUpdateView,
    LowStockAlertListView,
    StockEntryCreateView,
    StockEntryListView,
)

app_name = "inventory"

urlpatterns = [
    path("ingredients/", IngredientListView.as_view(), name="ingredients"),
    path("ingredients/new/", IngredientCreateView.as_view(), name="ingredient-create"),
    path("ingredients/<int:pk>/edit/", IngredientUpdateView.as_view(), name="ingredient-edit"),
    path("stock/", StockEntryListView.as_view(), name="stock-entries"),
    path("stock/new/", StockEntryCreateView.as_view(), name="stock-entry-create"),
    path("alerts/", LowStockAlertListView.as_view(), name="alerts"),
]
