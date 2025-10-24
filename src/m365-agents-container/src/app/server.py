"""aiohttp server startup utilities (extracted from start_server.py)."""
from __future__ import annotations

from datetime import datetime
from os import environ
from typing import Any

from aiohttp import web
from aiohttp.web import Application, Request, Response, run_app
from microsoft_agents.hosting.aiohttp import (CloudAdapter,
                                              jwt_authorization_middleware,
                                              start_agent_process)
from microsoft_agents.hosting.core import (AgentApplication,
                                           AgentAuthConfiguration)


def build_app(
    *,
    agent_application: AgentApplication,
    auth_configuration: AgentAuthConfiguration,
) -> Application:
    """Create and configure the aiohttp Application instance."""

    async def entry_point(req: Request) -> Response:
        agent: AgentApplication = req.app["agent_app"]
        adapter: CloudAdapter = req.app["adapter"]
        return await start_agent_process(req, agent, adapter)

    @web.middleware
    async def health_auth_bypass_middleware(request: Request, handler):  # type: ignore[override]
        if request.path in ("/healthz", "/health"):
            return web.json_response(
                {
                    "status": "ok",
                    "service": "m365-agents",
                    "time": datetime.utcnow().isoformat() + "Z",
                }
            )
        return await handler(request)

    app = Application(
        middlewares=[health_auth_bypass_middleware, jwt_authorization_middleware]
    )
    app.router.add_post("/api/messages", entry_point)

    async def _health_placeholder(_: Request) -> Response:  # noqa: D401
        return Response(text="")

    app.router.add_get("/healthz", _health_placeholder)
    app.router.add_get("/health", _health_placeholder)
    app["agent_configuration"] = auth_configuration
    app["agent_app"] = agent_application
    app["adapter"] = agent_application.adapter
    return app


def run_server(app: Application) -> None:
    """Run the aiohttp application on the configured port."""
    port_val = int(environ.get("PORT", 3978))
    run_app(app, host="0.0.0.0", port=port_val)


__all__ = ["build_app", "run_server"]
