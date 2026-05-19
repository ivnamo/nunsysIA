from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


ERPOrderStatus = Literal["pending", "shipped", "cancelled"]


class Customer(BaseModel):
    customer_id: str = Field(min_length=1)
    company_name: str
    contact_name: str | None = None
    country: str
    city: str


class OrderLine(BaseModel):
    order_id: int
    product_id: int
    product_name: str
    unit_price: Decimal
    quantity: int
    discount: Decimal = Decimal("0")


class OrderSummary(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    order_id: int
    customer_id: str
    customer_name: str
    order_date: date
    required_date: date | None = None
    shipped_date: date | None = None
    erp_status: ERPOrderStatus
    amount: Decimal


class MonthlyOrderSummary(BaseModel):
    year: int
    month: int
    orders: list[OrderSummary]
