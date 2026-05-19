from datetime import date
from typing import Literal

from pydantic import BaseModel


ProductionStatus = Literal["in_progress", "blocked", "delayed", "finished"]


class ProductionOrder(BaseModel):
    order_id: int
    production_status: ProductionStatus
    blocked_reason: str | None = None
    delay_reason: str | None = None
    estimated_finish_date: date


class ProductionOrdersResponse(BaseModel):
    orders: list[ProductionOrder]


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"
