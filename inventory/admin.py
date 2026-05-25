from django.contrib import admin

from inventory.models import Ingredient, LowStockAlert, Recipe, StockEntry, Supplier


@admin.register(Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    list_display = ("name", "tenant", "branch", "current_stock", "reorder_level", "is_active")
    list_filter = ("tenant", "branch", "is_active")


@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ("name", "tenant", "branch", "phone", "is_active")


@admin.register(StockEntry)
class StockEntryAdmin(admin.ModelAdmin):
    list_display = ("ingredient", "tenant", "branch", "movement_type", "quantity", "created_at")
    list_filter = ("tenant", "branch", "movement_type")


@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    list_display = ("product", "ingredient", "quantity_per_unit", "tenant")


@admin.register(LowStockAlert)
class LowStockAlertAdmin(admin.ModelAdmin):
    list_display = ("ingredient", "tenant", "branch", "status", "current_stock", "reorder_level", "created_at")
    list_filter = ("status", "tenant", "branch")
