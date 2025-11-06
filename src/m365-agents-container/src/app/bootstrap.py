"""Public main() entry point; adds optional telemetry bootstrap."""
from __future__ import annotations

import os
from typing import Optional

# Import handlers to register routes via decorators (side-effect registration)
from ..api import handlers  # noqa: F401  # pylint: disable=unused-import
from .config import AGENT_APP, CONNECTION_MANAGER
from .logging import configure_root_logging
from .server import build_app, run_server

try:  # Agent Framework observability is optional
    from agent_framework.observability import \
        setup_observability  # type: ignore
except ImportError:  # pragma: no cover - if dependency not present
    setup_observability = None  # type: ignore


def _maybe_enable_observability() -> None:
    """Enable telemetry via Agent Framework zero‑code helper if available.

    Activation conditions:
    - Library import succeeded AND
    - Either APPLICATIONINSIGHTS_CONNECTION_STRING is set OR ENABLE_OTEL=true.
    This avoids unnecessary overhead when telemetry isn't configured.
    """
    if setup_observability is None:  # library not installed
        return
    ai_conn: Optional[str] = os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING")
    enable_otel_flag = os.getenv("ENABLE_OTEL", "").lower() == "true"
    if ai_conn or enable_otel_flag:
        # setup_observability reads env vars (conn str, OTLP endpoint, flags)
        setup_observability()


def main() -> None:  # pragma: no cover - thin orchestration
    # Initialize telemetry first so logging captures early spans
    _maybe_enable_observability()
    configure_root_logging()
    app = build_app(
        agent_application=AGENT_APP,
        auth_configuration=(
            CONNECTION_MANAGER.get_default_connection_configuration()
        ),
    )
    run_server(app)


__all__ = ["main"]
