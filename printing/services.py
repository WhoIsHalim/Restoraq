from __future__ import annotations

from django.conf import settings
from django.utils import timezone

from printing.models import BranchPrinterConfig, PrintJob


class PrintService:
    @staticmethod
    def _customer_payload(order) -> dict:
        return {
            "order_number": order.order_number,
            "type": "customer",
            "with_prices": True,
            "order_type": order.order_type,
            "total": str(order.total_amount),
            "items": [
                {
                    "name": item.name_snapshot,
                    "qty": str(item.quantity),
                    "unit_price": str(item.unit_price),
                    "line_total": str(item.line_total),
                }
                for item in order.items.all()
            ],
        }

    @staticmethod
    def _kitchen_payload(order) -> dict:
        return {
            "order_number": order.order_number,
            "type": "kitchen",
            "with_prices": False,
            "order_type": order.order_type,
            "items": [
                {"name": item.name_snapshot, "qty": str(item.quantity), "notes": item.notes}
                for item in order.items.all()
            ],
        }

    @staticmethod
    def _delivery_payload(order) -> dict:
        return {
            "order_number": order.order_number,
            "type": "delivery",
            "with_prices": True,
            "order_type": order.order_type,
            "customer_name": order.customer_name_snapshot,
            "customer_phone": order.customer_phone_snapshot,
            "customer_address": order.customer_address_snapshot,
            "total": str(order.total_amount),
            "items": [
                {
                    "name": item.name_snapshot,
                    "qty": str(item.quantity),
                    "unit_price": str(item.unit_price),
                    "line_total": str(item.line_total),
                }
                for item in order.items.all()
            ],
        }

    @classmethod
    def enqueue_order_prints(cls, *, order) -> list[PrintJob]:
        config = BranchPrinterConfig.objects.filter(branch=order.branch, tenant=order.tenant).first()
        if not config or not config.auto_print:
            return []

        jobs = []
        customer_job = PrintJob.objects.create(
            tenant=order.tenant,
            branch=order.branch,
            order=order,
            printer=config.customer_printer,
            template_type=PrintJob.TEMPLATE_CUSTOMER,
            payload=cls._customer_payload(order),
        )
        jobs.append(customer_job)

        kitchen_job = PrintJob.objects.create(
            tenant=order.tenant,
            branch=order.branch,
            order=order,
            printer=config.kitchen_printer,
            template_type=PrintJob.TEMPLATE_KITCHEN,
            payload=cls._kitchen_payload(order),
        )
        jobs.append(kitchen_job)
        return jobs

    @classmethod
    def create_manual_job(cls, *, order, template_type: str) -> PrintJob:
        config = BranchPrinterConfig.objects.filter(branch=order.branch, tenant=order.tenant).first()
        if not config:
            raise ValueError("Printer configuration is missing.")
        if template_type == PrintJob.TEMPLATE_CUSTOMER:
            printer = config.customer_printer
            payload = cls._customer_payload(order)
        elif template_type == PrintJob.TEMPLATE_KITCHEN:
            printer = config.kitchen_printer
            payload = cls._kitchen_payload(order)
        elif template_type == PrintJob.TEMPLATE_DELIVERY:
            printer = config.delivery_printer or config.customer_printer
            payload = cls._delivery_payload(order)
        else:
            raise ValueError("Invalid template type.")
        if not printer:
            raise ValueError("Printer is not configured for this template.")
        return PrintJob.objects.create(
            tenant=order.tenant,
            branch=order.branch,
            order=order,
            printer=printer,
            template_type=template_type,
            payload=payload,
        )

    @staticmethod
    def acknowledge(job: PrintJob):
        job.status = PrintJob.STATUS_ACKED
        job.acked_at = timezone.now()
        job.save(update_fields=["status", "acked_at", "updated_at"])

    @staticmethod
    def mark_sent(job: PrintJob):
        job.status = PrintJob.STATUS_SENT
        job.sent_at = timezone.now()
        job.attempts += 1
        job.save(update_fields=["status", "sent_at", "attempts", "updated_at"])

    @staticmethod
    def mark_failed(job: PrintJob, error: str):
        job.status = PrintJob.STATUS_FAILED
        job.attempts += 1
        job.last_error = error[:1000]
        job.save(update_fields=["status", "attempts", "last_error", "updated_at"])

    @staticmethod
    def qz_sign(payload: str) -> str:
        import hashlib
        import hmac

        secret = settings.SECRET_KEY.encode("utf-8")
        return hmac.new(secret, payload.encode("utf-8"), hashlib.sha256).hexdigest()
