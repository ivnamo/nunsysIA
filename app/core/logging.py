from __future__ import annotations

import logging


def configure_logging(log_level: str) -> None:
    level = _coerce_log_level(log_level)
    root_logger = logging.getLogger()
    if not root_logger.handlers:
        logging.basicConfig(
            level=level,
            format="%(levelname)s:%(name)s:%(message)s",
        )
    root_logger.setLevel(level)
    logging.getLogger("app").setLevel(level)
    for logger_name in ("httpx", "httpcore", "chromadb"):
        logging.getLogger(logger_name).setLevel(logging.WARNING)


def _coerce_log_level(value: str) -> int:
    normalized = (value or "INFO").upper()
    return getattr(logging, normalized, logging.INFO)
