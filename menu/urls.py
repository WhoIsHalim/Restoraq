from django.urls import path

from menu.views import (
    CategoryCreateView,
    CategoryListView,
    CategoryUpdateView,
    ProductCreateView,
    ProductListView,
    ProductRecipeManageView,
    ProductUpdateView,
    PublicMenuView,
)

app_name = "menu"

urlpatterns = [
    path("qr/<slug:tenant_slug>/", PublicMenuView.as_view(), name="public-menu"),
    path("categories/", CategoryListView.as_view(), name="categories"),
    path("categories/new/", CategoryCreateView.as_view(), name="category-create"),
    path("categories/<int:pk>/edit/", CategoryUpdateView.as_view(), name="category-edit"),
    path("products/", ProductListView.as_view(), name="products"),
    path("products/new/", ProductCreateView.as_view(), name="product-create"),
    path("products/<int:pk>/edit/", ProductUpdateView.as_view(), name="product-edit"),
    path("products/<int:pk>/recipes/", ProductRecipeManageView.as_view(), name="product-recipes"),
]
