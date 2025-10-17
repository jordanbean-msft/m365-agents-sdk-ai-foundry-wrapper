from os import environ

from aiohttp.web import Application, Request, Response, run_app
from microsoft_agents.hosting.aiohttp import (CloudAdapter,
                                              jwt_authorization_middleware,
                                              start_agent_process)
from microsoft_agents.hosting.core import (AgentApplication,
                                           AgentAuthConfiguration)


def start_server(
    agent_application: AgentApplication, auth_configuration: AgentAuthConfiguration
):
    async def entry_point(req: Request) -> Response:
        agent: AgentApplication = req.app["agent_app"]
        adapter: CloudAdapter = req.app["adapter"]
        return await start_agent_process(
            req,
            agent,
            adapter,
        )

    APP = Application(middlewares=[jwt_authorization_middleware])
    APP.router.add_post("/api/messages", entry_point)
    APP["agent_configuration"] = auth_configuration
    APP["agent_app"] = agent_application
    APP["adapter"] = agent_application.adapter

    try:
        run_app(APP, host="0.0.0.0", port=environ.get("PORT", 3978))
    except Exception as error:
        raise error
