from __future__ import annotations

from crm.models import Customer


class CustomerService:
    @staticmethod
    def resolve_or_create_for_delivery(*, tenant, branch, customer_payload: dict):
        customer_id = customer_payload.get("id")
        name = (customer_payload.get("name") or "").strip()
        phone = (customer_payload.get("phone") or "").strip()
        address = (customer_payload.get("address") or "").strip()

        customer = None
        if customer_id:
            customer = Customer.objects.filter(tenant=tenant, id=customer_id, is_active=True).first()

        if not customer and phone:
            customer = Customer.objects.filter(tenant=tenant, phone=phone, is_active=True).first()

        if customer:
            updated_fields: list[str] = []
            if name and customer.name != name:
                customer.name = name
                updated_fields.append("name")
            if branch and customer.branch_id != branch.id:
                customer.branch = branch
                updated_fields.append("branch")
            if address and customer.notes != address:
                customer.notes = address
                updated_fields.append("notes")
            if updated_fields:
                updated_fields.append("updated_at")
                customer.save(update_fields=updated_fields)
            return customer

        if not name:
            name = "عميل دليفري" if tenant.default_language.startswith("ar") else "Delivery Customer"

        return Customer.objects.create(
            tenant=tenant,
            branch=branch,
            name=name,
            phone=phone,
            notes=address,
            is_active=True,
        )
