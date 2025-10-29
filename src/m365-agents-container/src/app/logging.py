"""Logging configuration utilities.

Separated so other modules can import logging configuration without causing
side-effects or circular imports.
"""
from __future__ import annotations

import logging
import os
from typing import Optional


def configure_root_logging(level_name: Optional[str] = None) -> None:
    """Configure root logging only once.

    Parameters
    ----------
    level_name: Optional[str]
        Explicit level name (e.g. "INFO"). If omitted, LOG_LEVEL env var or
        INFO is used.
    """
    log_level_name = (level_name or os.getenv("LOG_LEVEL", "INFO")).upper()
    level = getattr(logging, log_level_name, logging.INFO)

    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    if root_logger.handlers:
        for handler in root_logger.handlers:
            handler.setLevel(level)
    else:
        import sys
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(level)
        formatter = logging.Formatter(
            "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
        )
        handler.setFormatter(formatter)
        root_logger.addHandler(handler)

    # Ensure dependency loggers respect chosen level
    logging.getLogger("microsoft_agents").setLevel(level)


__all__ = ["configure_root_logging"]
