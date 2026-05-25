from __future__ import annotations

from menu.models import Category, Product


class MenuService:
    @staticmethod
    def build_menu_payload(tenant, branch=None) -> dict:
        categories_qs = Category.objects.filter(tenant=tenant, is_active=True)
        products_qs = Product.objects.filter(tenant=tenant, is_active=True)
        if branch:
            categories_qs = categories_qs.filter(branch__in=[branch, None])
            products_qs = products_qs.filter(branch__in=[branch, None])
        categories = list(categories_qs.values("id", "name", "display_order").order_by("display_order", "name"))
        products = list(
            products_qs.values(
                "id",
                "category_id",
                "name",
                "sku",
                "price",
                "tax_rate",
                "is_tax_inclusive",
                "image",
            ).order_by("name")
        )
        return {"categories": categories, "products": products}
