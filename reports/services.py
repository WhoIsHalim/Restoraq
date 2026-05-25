from __future__ import annotations

from collections import Counter
from datetime import date, timedelta
from decimal import Decimal

from django.db.models import Count, DecimalField, F, Sum
from django.db.models.functions import TruncDate

from hr.models import PayrollRecord
from inventory.models import StockEntry
from orders.models import Order, OrderItem
from restaurants.models import Branch


class ReportService:
    PERIODS = {
        "daily": 1,
        "weekly": 7,
        "biweekly": 14,
        "monthly": 30,
        "quarterly": 90,
        "yearly": 365,
    }

    @staticmethod
    def daily_sales(*, tenant, branch=None, day: date | None = None) -> Decimal:
        day = day or date.today()
        qs = Order.objects.filter(tenant=tenant, created_at__date=day, status=Order.STATUS_CONFIRMED)
        if branch:
            qs = qs.filter(branch=branch)
        return qs.aggregate(total=Sum("total_amount"))["total"] or Decimal("0")

    @staticmethod
    def monthly_sales(*, tenant, branch=None, year: int | None = None, month: int | None = None) -> Decimal:
        day = date.today()
        year = year or day.year
        month = month or day.month
        qs = Order.objects.filter(
            tenant=tenant,
            created_at__year=year,
            created_at__month=month,
            status=Order.STATUS_CONFIRMED,
        )
        if branch:
            qs = qs.filter(branch=branch)
        return qs.aggregate(total=Sum("total_amount"))["total"] or Decimal("0")

    @staticmethod
    def best_and_least_selling(*, tenant, branch=None) -> dict:
        qs = OrderItem.objects.filter(tenant=tenant, order__status=Order.STATUS_CONFIRMED)
        if branch:
            qs = qs.filter(branch=branch)
        counter = Counter()
        for item in qs.values("name_snapshot", "quantity"):
            counter[item["name_snapshot"]] += float(item["quantity"])
        if not counter:
            return {"best": None, "least": None}
        best = counter.most_common(1)[0]
        least = counter.most_common()[-1]
        return {"best": best, "least": least}

    @classmethod
    def get_period_bounds(cls, period: str) -> tuple[date, date]:
        days = cls.PERIODS.get(period, 30)
        end_day = date.today()
        start_day = end_day - timedelta(days=days - 1)
        return start_day, end_day

    @staticmethod
    def _sales_qs(*, tenant, branch=None, start_day: date, end_day: date):
        qs = Order.objects.filter(
            tenant=tenant,
            status=Order.STATUS_CONFIRMED,
            created_at__date__gte=start_day,
            created_at__date__lte=end_day,
        )
        if branch:
            qs = qs.filter(branch=branch)
        return qs

    @staticmethod
    def _stock_expense_qs(*, tenant, branch=None, start_day: date, end_day: date):
        qs = StockEntry.objects.filter(
            tenant=tenant,
            movement_type=StockEntry.MOVEMENT_IN,
            created_at__date__gte=start_day,
            created_at__date__lte=end_day,
        )
        if branch:
            qs = qs.filter(branch=branch)
        return qs

    @staticmethod
    def _payroll_expense_qs(*, tenant, branch=None, start_day: date, end_day: date):
        qs = PayrollRecord.objects.filter(
            tenant=tenant,
            status=PayrollRecord.STATUS_PAID,
            period_end__gte=start_day,
            period_end__lte=end_day,
        )
        if branch:
            qs = qs.filter(branch=branch)
        return qs

    @classmethod
    def expense_total(cls, *, tenant, branch=None, start_day: date, end_day: date) -> Decimal:
        stock_total = (
            cls._stock_expense_qs(tenant=tenant, branch=branch, start_day=start_day, end_day=end_day)
            .aggregate(
                total=Sum(
                    F("quantity") * F("unit_cost"),
                    output_field=DecimalField(max_digits=14, decimal_places=3),
                )
            )
            .get("total")
            or Decimal("0")
        )
        payroll_total = (
            cls._payroll_expense_qs(tenant=tenant, branch=branch, start_day=start_day, end_day=end_day)
            .aggregate(total=Sum("net_amount"))
            .get("total")
            or Decimal("0")
        )
        return (stock_total + payroll_total).quantize(Decimal("0.01"))

    @classmethod
    def period_summary(cls, *, tenant, branch=None, period: str = "monthly") -> dict:
        start_day, end_day = cls.get_period_bounds(period)
        sales = cls._sales_qs(tenant=tenant, branch=branch, start_day=start_day, end_day=end_day).aggregate(
            total=Sum("total_amount")
        ).get("total") or Decimal("0")
        expenses = cls.expense_total(tenant=tenant, branch=branch, start_day=start_day, end_day=end_day)
        net = (sales - expenses).quantize(Decimal("0.01"))
        return {
            "period": period,
            "start_day": start_day,
            "end_day": end_day,
            "sales": sales,
            "expenses": expenses,
            "net_profit": net,
        }

    @classmethod
    def sales_vs_expense_series(cls, *, tenant, branch=None, period: str = "monthly") -> dict:
        start_day, end_day = cls.get_period_bounds(period)
        sales_rows = (
            cls._sales_qs(tenant=tenant, branch=branch, start_day=start_day, end_day=end_day)
            .annotate(day=TruncDate("created_at"))
            .values("day")
            .annotate(total=Sum("total_amount"))
            .order_by("day")
        )
        stock_rows = (
            cls._stock_expense_qs(tenant=tenant, branch=branch, start_day=start_day, end_day=end_day)
            .annotate(day=TruncDate("created_at"))
            .values("day")
            .annotate(
                total=Sum(
                    F("quantity") * F("unit_cost"),
                    output_field=DecimalField(max_digits=14, decimal_places=3),
                )
            )
            .order_by("day")
        )

        sales_map = {row["day"]: float(row["total"] or 0) for row in sales_rows}
        stock_map = {row["day"]: float(row["total"] or 0) for row in stock_rows}

        labels: list[str] = []
        sales_data: list[float] = []
        expense_data: list[float] = []

        cursor = start_day
        while cursor <= end_day:
            labels.append(cursor.strftime("%Y-%m-%d"))
            sales_data.append(round(sales_map.get(cursor, 0.0), 2))
            expense_data.append(round(stock_map.get(cursor, 0.0), 2))
            cursor += timedelta(days=1)

        return {
            "labels": labels,
            "sales": sales_data,
            "expenses": expense_data,
        }

    @classmethod
    def branch_financial_breakdown(cls, *, tenant, period: str = "monthly") -> list[dict]:
        start_day, end_day = cls.get_period_bounds(period)
        rows: list[dict] = []
        for branch in Branch.objects.filter(tenant=tenant, is_active=True).order_by("name"):
            sales = cls._sales_qs(tenant=tenant, branch=branch, start_day=start_day, end_day=end_day).aggregate(
                total=Sum("total_amount")
            ).get("total") or Decimal("0")
            expenses = cls.expense_total(tenant=tenant, branch=branch, start_day=start_day, end_day=end_day)
            rows.append(
                {
                    "branch": branch,
                    "sales": sales,
                    "expenses": expenses,
                    "net_profit": (sales - expenses).quantize(Decimal("0.01")),
                }
            )
        return rows

    @classmethod
    def order_status_breakdown(cls, *, tenant, branch=None, period: str = "monthly") -> dict:
        start_day, end_day = cls.get_period_bounds(period)
        qs = Order.objects.filter(tenant=tenant, created_at__date__gte=start_day, created_at__date__lte=end_day)
        if branch:
            qs = qs.filter(branch=branch)
        rows = qs.values("status").annotate(total=Count("id"))
        status_map = {row["status"]: int(row["total"]) for row in rows}
        return {
            "draft": status_map.get(Order.STATUS_DRAFT, 0),
            "confirmed": status_map.get(Order.STATUS_CONFIRMED, 0),
            "cancelled": status_map.get(Order.STATUS_CANCELLED, 0),
        }

    @classmethod
    def top_products_series(cls, *, tenant, branch=None, period: str = "monthly", limit: int = 7) -> dict:
        start_day, end_day = cls.get_period_bounds(period)
        qs = OrderItem.objects.filter(
            tenant=tenant,
            order__status=Order.STATUS_CONFIRMED,
            order__created_at__date__gte=start_day,
            order__created_at__date__lte=end_day,
        )
        if branch:
            qs = qs.filter(branch=branch)
        rows = (
            qs.values("name_snapshot")
            .annotate(total_qty=Sum("quantity"))
            .order_by("-total_qty", "name_snapshot")[:limit]
        )
        labels = [row["name_snapshot"] for row in rows]
        values = [float(row["total_qty"] or 0) for row in rows]
        return {"labels": labels, "values": values}
