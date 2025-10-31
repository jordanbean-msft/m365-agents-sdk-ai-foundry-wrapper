"""Environment configuration & hosting object wiring.

Original contents moved from the top-level `config.py` for better modularity.
A thin compatibility shim remains in the legacy location importing these
symbols so external imports continue to function.
"""
from __future__ import annotations

import logging
from os import environ
from typing import List

from azure.identity import DefaultAzureCredential
from azure.identity.aio import \
    DefaultAzureCredential as AsyncDefaultAzureCredential
from dotenv import load_dotenv
from microsoft_agents.activity import load_configuration_from_env
from microsoft_agents.authentication.msal import MsalConnectionManager
from microsoft_agents.hosting.aiohttp import CloudAdapter
from microsoft_agents.hosting.core import (AgentApplication, Authorization,
                                           MemoryStorage, TurnState)

logger = logging.getLogger(__name__)

load_dotenv()
agents_sdk_config = load_configuration_from_env(environ)

AZURE_AI_PROJECT_ENDPOINT: str = environ.get("AZURE_AI_PROJECT_ENDPOINT", "")
AZURE_AI_FOUNDRY_AGENT_ID: str = environ.get("AZURE_AI_FOUNDRY_AGENT_ID", "")
AZURE_AI_MODEL_DEPLOYMENT_NAME: str = environ.get(
    "AZURE_AI_MODEL_DEPLOYMENT_NAME", ""
)

# Feature flag: enable metadata card after streaming responses
ENABLE_RESPONSE_METADATA_CARD: bool = environ.get(
    "ENABLE_RESPONSE_METADATA_CARD", "false"
).lower() in {"1", "true", "yes", "on"}

RAW_RESET_KEYWORDS = environ.get("RESET_COMMAND_KEYWORDS", "reset,restart,new")
RESET_COMMAND_KEYWORDS: List[str] = [
    k.strip().lower() for k in RAW_RESET_KEYWORDS.split(",") if k.strip()
]

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

credential = DefaultAzureCredential()
async_credential = AsyncDefaultAzureCredential()

__all__ = [
    "AGENT_APP",
    "AZURE_AI_PROJECT_ENDPOINT",
    "AZURE_AI_FOUNDRY_AGENT_ID",
    "AZURE_AI_MODEL_DEPLOYMENT_NAME",
    "ENABLE_RESPONSE_METADATA_CARD",
    "RESET_COMMAND_KEYWORDS",
    "CONNECTION_MANAGER",
    "async_credential",
]
