import sqlite3
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from app.erp.schemas import Customer, OrderLine, OrderSummary


class NorthwindRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection
        self._connection.row_factory = sqlite3.Row

    def get_customer(self, customer_id: str) -> Customer | None:
        row = self._connection.execute(
            """
            SELECT customer_id, company_name, contact_name, country, city
            FROM customers
            WHERE customer_id = ?
            """,
            (customer_id.upper(),),
        ).fetchone()
        return self._customer_from_row(row) if row else None

    def get_customer_by_order(self, order_id: int) -> Customer | None:
        row = self._connection.execute(
            """
            SELECT c.customer_id, c.company_name, c.contact_name, c.country, c.city
            FROM customers c
            JOIN orders o ON o.customer_id = c.customer_id
            WHERE o.order_id = ?
            """,
            (order_id,),
        ).fetchone()
        return self._customer_from_row(row) if row else None

    def get_pending_orders_by_customer(self, customer_id: str) -> list[OrderSummary]:
        rows = self._connection.execute(
            """
            SELECT
                o.order_id,
                o.customer_id,
                c.company_name AS customer_name,
                o.order_date,
                o.required_date,
                o.shipped_date,
                o.erp_status,
                COALESCE(SUM(od.unit_price * od.quantity * (1 - od.discount)), 0) AS amount
            FROM orders o
            JOIN customers c ON c.customer_id = o.customer_id
            LEFT JOIN order_details od ON od.order_id = o.order_id
            WHERE o.customer_id = ?
              AND o.erp_status = 'pending'
            GROUP BY
                o.order_id,
                o.customer_id,
                c.company_name,
                o.order_date,
                o.required_date,
                o.shipped_date,
                o.erp_status
            ORDER BY o.order_id
            """,
            (customer_id.upper(),),
        ).fetchall()
        return [self._order_summary_from_row(row) for row in rows]

    def get_orders_by_month(self, year: int, month: int) -> list[OrderSummary]:
        month_prefix = f"{year:04d}-{month:02d}-%"
        rows = self._connection.execute(
            """
            SELECT
                o.order_id,
                o.customer_id,
                c.company_name AS customer_name,
                o.order_date,
                o.required_date,
                o.shipped_date,
                o.erp_status,
                COALESCE(SUM(od.unit_price * od.quantity * (1 - od.discount)), 0) AS amount
            FROM orders o
            JOIN customers c ON c.customer_id = o.customer_id
            LEFT JOIN order_details od ON od.order_id = o.order_id
            WHERE o.order_date LIKE ?
            GROUP BY
                o.order_id,
                o.customer_id,
                c.company_name,
                o.order_date,
                o.required_date,
                o.shipped_date,
                o.erp_status
            ORDER BY o.order_id
            """,
            (month_prefix,),
        ).fetchall()
        return [self._order_summary_from_row(row) for row in rows]

    def calculate_order_amount(self, order_id: int) -> Decimal | None:
        order_exists = self._connection.execute(
            "SELECT 1 FROM orders WHERE order_id = ?",
            (order_id,),
        ).fetchone()
        if not order_exists:
            return None

        row = self._connection.execute(
            """
            SELECT COALESCE(SUM(unit_price * quantity * (1 - discount)), 0) AS amount
            FROM order_details
            WHERE order_id = ?
            """,
            (order_id,),
        ).fetchone()
        return self._money(row["amount"])

    def get_order_lines(self, order_id: int) -> list[OrderLine]:
        rows = self._connection.execute(
            """
            SELECT
                od.order_id,
                od.product_id,
                p.product_name,
                od.unit_price,
                od.quantity,
                od.discount
            FROM order_details od
            JOIN products p ON p.product_id = od.product_id
            WHERE od.order_id = ?
            ORDER BY od.product_id
            """,
            (order_id,),
        ).fetchall()
        return [
            OrderLine(
                order_id=row["order_id"],
                product_id=row["product_id"],
                product_name=row["product_name"],
                unit_price=self._money(row["unit_price"]),
                quantity=row["quantity"],
                discount=Decimal(str(row["discount"])),
            )
            for row in rows
        ]

    @staticmethod
    def _customer_from_row(row: sqlite3.Row) -> Customer:
        return Customer(
            customer_id=row["customer_id"],
            company_name=row["company_name"],
            contact_name=row["contact_name"],
            country=row["country"],
            city=row["city"],
        )

    @classmethod
    def _order_summary_from_row(cls, row: sqlite3.Row) -> OrderSummary:
        return OrderSummary(
            order_id=row["order_id"],
            customer_id=row["customer_id"],
            customer_name=row["customer_name"],
            order_date=cls._date(row["order_date"]),
            required_date=cls._optional_date(row["required_date"]),
            shipped_date=cls._optional_date(row["shipped_date"]),
            erp_status=row["erp_status"],
            amount=cls._money(row["amount"]),
        )

    @staticmethod
    def _date(value: str) -> date:
        return date.fromisoformat(value)

    @classmethod
    def _optional_date(cls, value: str | None) -> date | None:
        return cls._date(value) if value else None

    @staticmethod
    def _money(value: Any) -> Decimal:
        return Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
