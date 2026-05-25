from __future__ import annotations

from orders.models import Order


class POSService:
    @staticmethod
    def build_status_payload(order: Order) -> dict:
        return {
            "order_id": order.id,
            "order_number": order.order_number,
            "status": order.status,
            "pending_sync": order.pending_sync,
            "order_type": order.order_type,
            "customer_name": order.customer_name_snapshot,
            "customer_phone": order.customer_phone_snapshot,
            "total_amount": str(order.total_amount),
            "client_order_uuid": str(order.client_order_uuid) if order.client_order_uuid else None,
        }
