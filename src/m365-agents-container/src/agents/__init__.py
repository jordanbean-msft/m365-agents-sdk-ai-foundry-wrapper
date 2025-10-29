"""Agent domain package.

Contains:
  factory.py  – Create ChatAgent instances from Foundry definitions.
  state.py    – In-memory conversation state helpers.
"""
from .factory import (SUPPORTED_PASSTHROUGH_TOOL_TYPES,
                      create_chat_agent_from_foundry)
from .state import (conversation_agents, conversation_last_activity,
                    conversation_threads, conversation_tool_resources,
                    reset_conversation)

__all__ = [
    "create_chat_agent_from_foundry",
    "SUPPORTED_PASSTHROUGH_TOOL_TYPES",
    "conversation_agents",
    "conversation_threads",
    "conversation_tool_resources",
    "conversation_last_activity",
    "reset_conversation",
]
