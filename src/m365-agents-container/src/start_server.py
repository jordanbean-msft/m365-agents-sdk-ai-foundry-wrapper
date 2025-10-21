from datetime import datetime
from os import environ

from aiohttp import web
from aiohttp.web import Application, Request, Response, run_app
from microsoft_agents.hosting.aiohttp import (CloudAdapter,
                                              jwt_authorization_middleware,
                                              start_agent_process)
from microsoft_agents.hosting.core import (AgentApplication,
                                           AgentAuthConfiguration)


def start_server(
    agent_application: AgentApplication,
    auth_configuration: AgentAuthConfiguration,
):
    async def entry_point(req: Request) -> Response:
        agent: AgentApplication = req.app["agent_app"]
        adapter: CloudAdapter = req.app["adapter"]
        return await start_agent_process(
            req,
            agent,
            adapter,
        )

    # Middleware: bypass auth for health endpoints (/healthz,/health)
    # App Gateway health probe does not send JWT, so we reply directly.
    @web.middleware
    async def health_auth_bypass_middleware(request: Request, handler):
        if request.path in ("/healthz", "/health"):
            # Lightweight liveness response (no downstream dependencies)
            return web.json_response(
                {
                    "status": "ok",
                    "service": "m365-agents",
                    "time": datetime.utcnow().isoformat() + "Z",
                }
            )
        return await handler(request)

    APP = Application(
        middlewares=[
            health_auth_bypass_middleware,
            jwt_authorization_middleware,
        ]
    )
    APP.router.add_post("/api/messages", entry_point)
    # Explicit health routes (middleware handles body) for introspection

    async def _health_placeholder(_: Request) -> Response:  # noqa: D401
        return Response(text="")

    APP.router.add_get("/healthz", _health_placeholder)
    APP.router.add_get("/health", _health_placeholder)
    APP["agent_configuration"] = auth_configuration
    APP["agent_app"] = agent_application
    APP["adapter"] = agent_application.adapter

    try:
        # Ensure port cast to int if provided as string
        port_val = int(environ.get("PORT", 3978))
        run_app(APP, host="0.0.0.0", port=port_val)
    except Exception as error:
        raise error
