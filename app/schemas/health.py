from typing import Literal

from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"


class ReadinessCheck(BaseModel):
    status: Literal["ok", "error"]
    detail: str


class ReadinessResponse(BaseModel):
    status: Literal["ok", "degraded"] = "ok"
    checks: dict[str, ReadinessCheck]
