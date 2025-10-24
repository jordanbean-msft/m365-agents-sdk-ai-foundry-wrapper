"""Public main() entry point consolidating startup steps."""
from __future__ import annotations

# Import handlers to register routes via decorators
from ..api import handlers  # noqa: F401
from .config import AGENT_APP, CONNECTION_MANAGER
from .logging import configure_root_logging
from .server import build_app, run_server


def main() -> None:  # pragma: no cover - thin orchestration
    configure_root_logging()
    app = build_app(
        agent_application=AGENT_APP,
        auth_configuration=CONNECTION_MANAGER.get_default_connection_configuration(),
    )
    run_server(app)


__all__ = ["main"]
