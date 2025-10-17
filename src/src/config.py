"""Configuration and wiring for the Azure AI Foundry streaming sample.

Centralizes env loading and construction of core SDK objects so that
`agent.py` can focus on handlers.
"""

from __future__ import annotations

import logging
from os import environ

from azure.identity import DefaultAzureCredential
from azure.identity.aio import (
    DefaultAzureCredential as AsyncDefaultAzureCredential,
)
from dotenv import load_dotenv
from microsoft_agents.activity import load_configuration_from_env
from microsoft_agents.authentication.msal import MsalConnectionManager
from microsoft_agents.hosting.aiohttp import CloudAdapter
from microsoft_agents.hosting.core import (
    AgentApplication,
    Authorization,
    MemoryStorage,
    TurnState,
)

logger = logging.getLogger(__name__)

load_dotenv()
agents_sdk_config = load_configuration_from_env(environ)

# Exported environment-based constants
AZURE_AI_PROJECT_ENDPOINT: str = environ.get("AZURE_AI_PROJECT_ENDPOINT", "")
AZURE_AI_FOUNDRY_AGENT_ID: str = environ.get("AZURE_AI_FOUNDRY_AGENT_ID", "")
AZURE_AI_MODEL_DEPLOYMENT_NAME: str = environ.get(
    "AZURE_AI_MODEL_DEPLOYMENT_NAME", ""
)

# Core hosting components
STORAGE = MemoryStorage()
CONNECTION_MANAGER = MsalConnectionManager(**agents_sdk_config)
ADAPTER = CloudAdapter(connection_manager=CONNECTION_MANAGER)
AUTHORIZATION = Authorization(STORAGE, CONNECTION_MANAGER, **agents_sdk_config)

AGENT_APP = AgentApplication[TurnState](
    storage=STORAGE,
    adapter=ADAPTER,
    authorization=AUTHORIZATION,
    **agents_sdk_config,
)

# Credentials (sync + async). Async credential is required by factory.
credential = DefaultAzureCredential()
async_credential = AsyncDefaultAzureCredential()

__all__ = [
    "AGENT_APP",
    "AZURE_AI_PROJECT_ENDPOINT",
    "AZURE_AI_FOUNDRY_AGENT_ID",
    "AZURE_AI_MODEL_DEPLOYMENT_NAME",
    "CONNECTION_MANAGER",
    "async_credential",
]
