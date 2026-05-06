# Copyright 2026 Lockheed Martin Corporation
# Lockheed Martin Proprietary Information

"""Distillery logger configuration."""

import json
import logging
import logging.config
import os
from pathlib import Path
from typing import Any

DEFAULT_LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {
            "format": "%(message)s",
            "datefmt": "[%X]",
        },
    },
    "handlers": {
        "rich": {
            "class": "rich.logging.RichHandler",
            "formatter": "default",
            "level": "INFO",
            "markup": True,
        },
    },
    "root": {
        "level": "INFO",
        "handlers": ["rich"],
    },
}


def setup_logger() -> None:
    """Apply loaded or default config to logger."""
    logging.config.dictConfig(_get_logger_config())


def _get_logger_config() -> dict[str, Any]:
    """Load logging configurations from a JSON file."""
    custom_configs = os.environ.get("DISTILLERY_LOGGING_CONFIG")
    if custom_configs is None:
        return DEFAULT_LOGGING_CONFIG
    config_path = Path(custom_configs)

    if not config_path.exists():
        msg = f"Logging config file not found: {config_path}"
        raise FileNotFoundError(msg)

    try:
        config_dict: dict[str, Any] = json.loads(config_path.read_text())
    except json.JSONDecodeError as e:
        msg = f"Invalid JSON in logging config file: {e}"
        raise ValueError(msg) from e

    return config_dict
