import pytest
from pydantic import ValidationError

from app.schemas.health import HealthResponse


def test_health_response_defaults_to_ok() -> None:
    response = HealthResponse()

    assert response.model_dump() == {"status": "ok"}


def test_health_response_rejects_unexpected_status() -> None:
    with pytest.raises(ValidationError):
        HealthResponse(status="down")
