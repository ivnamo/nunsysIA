import pytest
from pydantic import ValidationError

from app.schemas.health import HealthResponse, ReadinessCheck, ReadinessResponse


def test_health_response_defaults_to_ok() -> None:
    response = HealthResponse()

    assert response.model_dump() == {"status": "ok"}


def test_health_response_rejects_unexpected_status() -> None:
    with pytest.raises(ValidationError):
        HealthResponse(status="down")


def test_readiness_response_accepts_structured_checks() -> None:
    response = ReadinessResponse(
        checks={
            "production_api": ReadinessCheck(status="ok", detail="HTTP 200"),
            "chroma": ReadinessCheck(status="ok", detail="HTTP 200"),
        }
    )

    assert response.status == "ok"
    assert response.checks["production_api"].detail == "HTTP 200"


def test_readiness_response_rejects_unknown_status() -> None:
    with pytest.raises(ValidationError):
        ReadinessCheck(status="unknown", detail="bad")
