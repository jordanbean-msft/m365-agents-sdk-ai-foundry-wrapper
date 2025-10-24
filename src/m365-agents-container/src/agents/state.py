"""In-memory conversation state utilities (moved from conversation_state.py).

For production use, replace with a persistent store (Redis, Cosmos DB, etc.).
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Dict

from agent_framework import ChatAgent  # type: ignore
from agent_framework._threads import AgentThread  # type: ignore

logger = logging.getLogger(__name__)

conversation_agents: Dict[str, ChatAgent] = {}
conversation_threads: Dict[str, AgentThread] = {}
conversation_tool_resources: Dict[str, object] = {}
conversation_last_activity: Dict[str, datetime] = {}


def reset_conversation(conversation_id: str) -> None:
    removed_agent = conversation_agents.pop(conversation_id, None)
    removed_thread = conversation_threads.pop(conversation_id, None)
    conversation_tool_resources.pop(conversation_id, None)
    conversation_last_activity.pop(conversation_id, None)
    logger.info(
        "Conversation reset - ID=%s (agent=%s thread=%s)",
        conversation_id,
        bool(removed_agent),
        bool(removed_thread),
    )


__all__ = [
    "conversation_agents",
    "conversation_threads",
    "conversation_tool_resources",
    "conversation_last_activity",
    "reset_conversation",
]
