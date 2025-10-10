# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.

import pathlib
from os import environ, path

from agent import CustomEngineAgent
from aiohttp.web import Application, Request, Response, run_app
from config import DefaultConfig
from dotenv import load_dotenv
# Updated imports to reflect current package namespace (microsoft_agents)
from microsoft_agents.activity import load_configuration_from_env
from microsoft_agents.authentication.msal import MsalConnectionManager
from microsoft_agents.hosting.aiohttp import (CloudAdapter,
                                              jwt_authorization_decorator)
from microsoft_agents.hosting.core import (Authorization, MemoryStorage,
                                           UserState)

load_dotenv(path.join(path.dirname(__file__), ".env"))

CONFIG = DefaultConfig()

agents_sdk_config = load_configuration_from_env(environ)

STORAGE = MemoryStorage()
CONNECTION_MANAGER = MsalConnectionManager(**agents_sdk_config)
ADAPTER = CloudAdapter(connection_manager=CONNECTION_MANAGER)
AUTHORIZATION = Authorization(STORAGE, CONNECTION_MANAGER, **agents_sdk_config)

USER_STATE = UserState(STORAGE)

# Create the agent based on configuration
AGENT = CustomEngineAgent()

# Listen for incoming requests on /api/messages


@jwt_authorization_decorator
async def messages(req: Request) -> Response:
    adapter: CloudAdapter = req.app["adapter"]
    return await adapter.process(req, AGENT)

APP = Application()
APP.router.add_post("/api/messages", messages)

# Add static file handling for CSS, JS, etc.
static_path = pathlib.Path(__file__).parent / "public"
if static_path.exists():
    APP.router.add_static("/public", static_path)

APP["agent_configuration"] = CONFIG
APP["adapter"] = ADAPTER

if __name__ == "__main__":
    try:
        port = CONFIG.PORT
        host = environ.get("HOST", "0.0.0.0")
        print(f"\nServer listening on {host}:{port} for appId {CONFIG.CLIENT_ID}")
        run_app(APP, host=host, port=port)
    except Exception as exc:  # pragma: no cover
        raise exc
