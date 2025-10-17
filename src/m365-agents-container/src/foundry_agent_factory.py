"""Factory utilities for creating ChatAgents backed by Azure AI Foundry agents.

The logic here was previously embedded in `agent.py` and has been extracted for
clarity and testability.
"""

from __future__ import annotations

import logging
from typing import Any, Tuple

from agent_framework import ChatAgent
from agent_framework.azure import AzureAIAgentClient
from azure.core.credentials_async import AsyncTokenCredential

logger = logging.getLogger(__name__)

SUPPORTED_PASSTHROUGH_TOOL_TYPES: set[str] = {
    "code_interpreter",
    "file_search",
    "azure_ai_search",
    "bing_grounding",
    "bing_custom_search",
    "mcp",
    "openapi",
}


async def create_chat_agent_from_foundry(
    *,
    project_endpoint: str,
    agent_id: str,
    async_credential: AsyncTokenCredential,
) -> Tuple[ChatAgent, object | None]:
    """Create a `ChatAgent` mirroring an existing Azure AI Foundry agent.

    Returns a tuple of (ChatAgent, tool_resources) where tool_resources may be
    None if the agent definition was not retrieved.
    """
    chat_client = AzureAIAgentClient(
        async_credential=async_credential,
        project_endpoint=project_endpoint,
        agent_id=agent_id,
    )

    fetched_agent: Any | None = None
    try:
        fetched_agent = await chat_client.project_client.agents.get_agent(
            agent_id
        )
    except Exception as ex:  # noqa: BLE001
        logger.warning(
            "Failed to fetch Foundry agent '%s': %s. Creating minimal ChatAgent.",
            agent_id,
            ex,
        )

    chat_agent_kwargs: dict[str, Any] = {"chat_client": chat_client}
    tool_resources = None

    if fetched_agent is not None:
        foundry_tools: list[Any] = []
        try:
            for tool in getattr(fetched_agent, "tools", []) or []:
                tool_type = getattr(tool, "type", None)
                if tool_type in SUPPORTED_PASSTHROUGH_TOOL_TYPES:
                    foundry_tools.append(tool)
                elif tool_type == "function":
                    logger.info(
                        "Skipping function tool (no local impl): %s",
                        getattr(
                            getattr(tool, "function", {}),
                            "name",
                            "<unknown>",
                        ),
                    )
        except Exception as tool_ex:  # noqa: BLE001
            logger.warning("Error parsing Foundry tools: %s", tool_ex)

        chat_agent_kwargs.update(
            {
                "name": getattr(fetched_agent, "name", None) or None,
                "description": getattr(
                    fetched_agent, "description", None
                )
                or None,
                "instructions": getattr(
                    fetched_agent, "instructions", None
                )
                or None,
                "model_id": getattr(fetched_agent, "model", None) or None,
                "tools": foundry_tools if foundry_tools else None,
            }
        )

        temperature = getattr(fetched_agent, "temperature", None)
        top_p = getattr(fetched_agent, "top_p", None)
        if temperature is not None:
            chat_agent_kwargs["temperature"] = temperature
        if top_p is not None:
            chat_agent_kwargs["top_p"] = top_p

        tool_resources = getattr(fetched_agent, "tool_resources", None)
        logger.info(
            "Instantiated ChatAgent from Foundry '%s' (model=%s, temp=%s, top_p=%s, tools=%d)",
            getattr(fetched_agent, "name", agent_id),
            getattr(fetched_agent, "model", None),
            temperature,
            top_p,
            len(foundry_tools),
        )
    else:
        logger.info("Instantiated minimal ChatAgent (agent_id=%s)", agent_id)

    agent = ChatAgent(**chat_agent_kwargs)
    return agent, tool_resources

__all__ = [
    "create_chat_agent_from_foundry",
    "SUPPORTED_PASSTHROUGH_TOOL_TYPES",
]
