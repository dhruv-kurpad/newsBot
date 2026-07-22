"""Shared logging and resilient error helpers."""

from __future__ import annotations

import logging
import sys
from typing import Any, Callable, TypeVar

T = TypeVar("T")

logger = logging.getLogger("newsbot")


def configure_logging(level: int = logging.INFO) -> None:
    """Configure application logging."""
    root = logging.getLogger()
    if not root.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(
            logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
        )
        root.addHandler(handler)
    root.setLevel(level)
    logging.getLogger("newsbot").setLevel(level)


def safe_call(fn: Callable[..., T], *args: Any, default: T, **kwargs: Any) -> T:
    """Call ``fn`` and return ``default`` on failure (log the error)."""
    try:
        return fn(*args, **kwargs)
    except Exception:  # noqa: BLE001 — intentional resilience helper
        logger.exception("safe_call suppressed error in %s", getattr(fn, "__name__", repr(fn)))
        return default
