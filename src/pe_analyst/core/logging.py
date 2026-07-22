"""Application logging infrastructure."""

import logging
import logging.config
from typing import Any

from pe_analyst.core.config import Settings, get_settings

DEFAULT_LOG_FORMAT = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"


def build_logging_config(settings: Settings) -> dict[str, Any]:
    """Build the logging configuration dictionary."""

    return {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "standard": {
                "format": DEFAULT_LOG_FORMAT,
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "standard",
                "level": settings.log_level,
            },
        },
        "root": {
            "handlers": ["console"],
            "level": settings.log_level,
        },
    }


def configure_logging(settings: Settings | None = None) -> None:
    """Configure application-wide logging."""

    resolved_settings = settings or get_settings()

    logging.config.dictConfig(build_logging_config(resolved_settings))


def get_logger(name: str) -> logging.Logger:
    """Return a logger for the requested module."""

    return logging.getLogger(name)
