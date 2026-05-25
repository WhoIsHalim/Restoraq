from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any
from uuid import UUID

from django.db import transaction
from django.db.models import Max
from django.utils import timezone

from audit.services import AuditService
from crm.services import CustomerService
from featureflags.services import FeatureService
from inventory.services import StockService
from menu.models import Product
from orders.models import Order, OrderItem, Payment, PaymentReview
from printing.services import PrintService


TWO_DP = Decimal("0.01")


@dataclass
class OrderTotals:
    subtotal: Decimal
    tax: Decimal
    total: Decimal


class OrderService:
    @classmethod
    def preview_order(cls, *, tenant, branch, items: list[dict[str, Any]]) -> OrderTotals:
        if not items:
            return OrderTotals(subtotal=Decimal("0.00"), tax=Decimal("0.00"), total=Decimal("0.00"))

        products = cls._get_products_map(tenant=tenant, branch=branch, item_rows=items)
        subtotal = Decimal("0")
        tax_amount = Decimal("0")
        total_amount = Decimal("0")
        for row in items:
            product = products[int(row["product_id"])]
            qty = Decimal(str(row.get("quantity", "1")))
            line_subtotal, line_tax, line_total = cls._line_totals(product, qty)
            subtotal += line_subtotal
            tax_amount += line_tax
            total_amount += line_total
        return OrderTotals(
            subtotal=subtotal.quantize(TWO_DP),
            tax=tax_amount.quantize(TWO_DP),
            total=total_amount.quantize(TWO_DP),
        )

    @classmethod
    @transaction.atomic
    def create_order(
        cls,
        *,
        tenant,
        branch,
        user,
        payload: dict[str, Any],
        source: str = "online",
    ) -> Order:
        client_uuid = payload.get("client_order_uuid")
        if client_uuid:
            try:
                client_uuid_obj = UUID(str(client_uuid))
            except ValueError:
                client_uuid_obj = None
            if client_uuid_obj:
                existing = Order.objects.filter(tenant=tenant, client_order_uuid=client_uuid_obj).first()
                if existing:
                    return existing
        else:
            client_uuid_obj = None

        items = payload.get("items", [])
        if not items:
            raise ValueError("Order items are required")

        totals = cls.preview_order(tenant=tenant, branch=branch, items=items)
        order_type = payload.get("order_type") or Order.TYPE_DINE_IN
        if order_type not in {Order.TYPE_DINE_IN, Order.TYPE_TAKEAWAY, Order.TYPE_DELIVERY}:
            raise ValueError("Invalid order type")

        customer = None
        customer_name = ""
        customer_phone = ""
        customer_address = ""
        if order_type == Order.TYPE_DELIVERY:
            customer_payload = payload.get("customer") or {}
            customer_name = (customer_payload.get("name") or "").strip()
            customer_phone = (customer_payload.get("phone") or "").strip()
            customer_address = (customer_payload.get("address") or "").strip()
            if not customer_phone:
                raise ValueError("Customer phone is required for delivery orders")
            customer = CustomerService.resolve_or_create_for_delivery(
                tenant=tenant,
                branch=branch,
                customer_payload=customer_payload,
            )
            customer_name = customer.name or customer_name
            customer_phone = customer.phone or customer_phone
            customer_address = customer.notes or customer_address

        order = Order.objects.create(
            tenant=tenant,
            branch=branch,
            order_number=cls._generate_order_number(tenant.id),
            subtotal=totals.subtotal,
            tax_amount=totals.tax,
            total_amount=totals.total,
            notes=payload.get("notes", ""),
            pending_sync=(source == "offline"),
            source=source,
            order_type=order_type,
            customer=customer,
            customer_name_snapshot=customer_name,
            customer_phone_snapshot=customer_phone,
            customer_address_snapshot=customer_address,
            client_order_uuid=client_uuid_obj,
            created_by=user,
        )

        products = cls._get_products_map(tenant=tenant, branch=branch, item_rows=items)
        for row in items:
            product = products[int(row["product_id"])]
            qty = Decimal(str(row.get("quantity", "1")))
            _line_subtotal, _line_tax, line_total = cls._line_totals(product, qty)
            OrderItem.objects.create(
                tenant=tenant,
                branch=branch,
                order=order,
                product=product,
                name_snapshot=product.name,
                quantity=qty,
                unit_price=product.price,
                line_total=line_total,
                notes=row.get("notes", ""),
            )

        payments = payload.get("payments", [])
        if not payments:
            payments = [{"method": Payment.METHOD_CASH, "amount": str(order.total_amount)}]

        for payment_row in payments:
            method = payment_row.get("method", Payment.METHOD_CASH)
            amount = Decimal(str(payment_row.get("amount", "0"))).quantize(TWO_DP)
            status = Payment.STATUS_CAPTURED
            requires_review = False
            if source == "offline" and method != Payment.METHOD_CASH:
                status = Payment.STATUS_CAPTURED_UNVERIFIED
                requires_review = True

            payment = Payment.objects.create(
                tenant=tenant,
                branch=branch,
                order=order,
                method=method,
                amount=amount,
                status=status,
                reference=payment_row.get("reference", ""),
                requires_manual_review=requires_review,
            )
            if requires_review:
                PaymentReview.objects.create(
                    tenant=tenant,
                    branch=branch,
                    payment=payment,
                    status=PaymentReview.STATUS_PENDING,
                )

        if FeatureService.is_enabled(tenant, "recipes"):
            StockService.apply_recipe_consumption(order=order, actor=user)

        PrintService.enqueue_order_prints(order=order)
        AuditService.log_action(
            tenant=tenant,
            branch=branch,
            user=user,
            action="order_created",
            model="orders.Order",
            object_id=str(order.id),
            metadata={"order_number": order.order_number, "source": source, "order_type": order_type},
        )
        return order

    @staticmethod
    def _get_products_map(*, tenant, branch, item_rows: list[dict[str, Any]]) -> dict[int, Product]:
        product_ids = {int(item["product_id"]) for item in item_rows}
        products = Product.objects.filter(tenant=tenant, id__in=product_ids, is_active=True)
        if branch:
            products = products.filter(branch__in=[branch, None])
        product_map = {product.id: product for product in products}
        missing = product_ids.difference(product_map.keys())
        if missing:
            raise ValueError(f"Invalid products in order payload: {sorted(missing)}")
        return product_map

    @staticmethod
    def _line_totals(product: Product, quantity: Decimal):
        unit_price = Decimal(product.price)
        line_amount = (unit_price * quantity).quantize(TWO_DP)
        tax_rate = Decimal(product.tax_rate)

        if product.is_tax_inclusive:
            divisor = Decimal("1") + (tax_rate / Decimal("100"))
            line_subtotal = (line_amount / divisor).quantize(TWO_DP)
            line_tax = (line_amount - line_subtotal).quantize(TWO_DP)
            line_total = line_amount
        else:
            line_subtotal = line_amount
            line_tax = (line_subtotal * tax_rate / Decimal("100")).quantize(TWO_DP)
            line_total = (line_subtotal + line_tax).quantize(TWO_DP)

        return line_subtotal, line_tax, line_total

    @staticmethod
    def _generate_order_number(tenant_id: int) -> str:
        today = timezone.localdate().strftime("%Y%m%d")
        latest = (
            Order.objects.filter(tenant_id=tenant_id, order_number__startswith=today)
            .aggregate(Max("order_number"))
            .get("order_number__max")
        )
        if latest and latest.count("-") == 1:
            counter = int(latest.split("-")[1]) + 1
        else:
            counter = 1
        return f"{today}-{counter:06d}"

    @classmethod
    def recalculate_order_totals(cls, *, order: Order) -> Order:
        """Recompute order subtotal/tax/total from current order items."""
        subtotal = Decimal("0")
        tax_total = Decimal("0")
        total = Decimal("0")
        for item in order.items.select_related("product").all():
            qty = Decimal(str(item.quantity))
            product = item.product
            line_subtotal, line_tax, line_total = cls._line_totals(product, qty)
            item.unit_price = product.price
            item.line_total = line_total
            item.save(update_fields=["unit_price", "line_total", "updated_at"])
            subtotal += line_subtotal
            tax_total += line_tax
            total += line_total
        order.subtotal = subtotal.quantize(TWO_DP)
        order.tax_amount = tax_total.quantize(TWO_DP)
        order.total_amount = total.quantize(TWO_DP)
        order.save(update_fields=["subtotal", "tax_amount", "total_amount", "updated_at"])
        return order

    @classmethod
    @transaction.atomic
    def set_kitchen_status(cls, *, order: Order, actor, kitchen_status: str) -> Order:
        if kitchen_status not in {
            Order.KITCHEN_PENDING,
            Order.KITCHEN_PREPARING,
            Order.KITCHEN_READY,
        }:
            raise ValueError("Invalid kitchen status")

        now = timezone.now()
        order.kitchen_status = kitchen_status
        if kitchen_status == Order.KITCHEN_PREPARING and not order.kitchen_started_at:
            order.kitchen_started_at = now
        if kitchen_status == Order.KITCHEN_READY:
            if not order.kitchen_started_at:
                order.kitchen_started_at = now
            order.kitchen_completed_at = now
            duration = now - order.kitchen_started_at
            order.cooking_duration_minutes = max(int(duration.total_seconds() // 60), 0)
        order.save(
            update_fields=[
                "kitchen_status",
                "kitchen_started_at",
                "kitchen_completed_at",
                "cooking_duration_minutes",
                "updated_at",
            ]
        )
        AuditService.log_action(
            tenant=order.tenant,
            branch=order.branch,
            user=actor,
            action="kitchen_status_changed",
            model="orders.Order",
            object_id=str(order.id),
            metadata={"order_number": order.order_number, "kitchen_status": kitchen_status},
        )
        return order
