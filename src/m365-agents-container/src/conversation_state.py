"""In-memory conversation state utilities.

For production use, replace these module-level dictionaries with a
pluggable persistence layer (Redis, Cosmos DB, etc.) suitable for
horizontal scaling and durability.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Dict

from agent_framework import ChatAgent  # type: ignore
from agent_framework._threads import AgentThread  # type: ignore

logger = logging.getLogger(__name__)

# Chat agent instances (mirroring Foundry agent configuration)
conversation_agents: Dict[str, ChatAgent] = {}
# Per-conversation thread (holds message history for the agent framework)
conversation_threads: Dict[str, AgentThread] = {}
# Tool resources fetched from Foundry agent definition (per conversation)
conversation_tool_resources: Dict[str, object] = {}
# Last user activity UTC timestamp (for timeout enforcement)
conversation_last_activity: Dict[str, datetime] = {}


def reset_conversation(conversation_id: str) -> None:
    """Clear all cached state for a conversation idempotently."""
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
