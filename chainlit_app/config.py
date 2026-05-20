import os
from functools import lru_cache

from pydantic import BaseModel


class ChainlitAppSettings(BaseModel):
    backend_api_base_url: str = "http://localhost:8000"
    backend_api_timeout_seconds: float = 30.0


@lru_cache
def get_chainlit_settings() -> ChainlitAppSettings:
    return ChainlitAppSettings(
        backend_api_base_url=os.getenv(
            "BACKEND_API_BASE_URL",
            "http://localhost:8000",
        ),
        backend_api_timeout_seconds=float(
            os.getenv("BACKEND_API_TIMEOUT_SECONDS", "30.0")
        ),
    )
