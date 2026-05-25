from django.contrib import admin

from menu.models import Category, ModifierGroup, ModifierOption, Product, ProductModifier


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "tenant", "branch", "display_order", "is_active")
    list_filter = ("tenant", "branch", "is_active")


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("name", "sku", "tenant", "branch", "price", "is_active")
    list_filter = ("tenant", "branch", "is_active")
    search_fields = ("name", "sku")


@admin.register(ModifierGroup)
class ModifierGroupAdmin(admin.ModelAdmin):
    list_display = ("name", "tenant", "branch", "is_required", "max_select")


@admin.register(ModifierOption)
class ModifierOptionAdmin(admin.ModelAdmin):
    list_display = ("name", "group", "tenant", "price_delta", "is_active")


@admin.register(ProductModifier)
class ProductModifierAdmin(admin.ModelAdmin):
    list_display = ("tenant", "product", "modifier_group")
