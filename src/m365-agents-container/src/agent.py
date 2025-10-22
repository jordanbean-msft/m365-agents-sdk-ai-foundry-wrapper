# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.

"""Bot handlers and per-conversation agent management.

This module now only contains the HTTP activity handlers and lightweight
conversation state. All heavy lifting (configuration + Foundry agent mapping)
has been moved to `config.py` and `foundry_agent_factory.py`.
"""

from __future__ import annotations

import logging
import re

from agent_framework import ChatAgent
from agent_framework._threads import AgentThread  # type: ignore
from microsoft_agents.activity import (Activity, ActivityTypes,
                                       SensitivityUsageInfo)
from microsoft_agents.hosting.core import TurnContext, TurnState

from .config import (AGENT_APP, AZURE_AI_FOUNDRY_AGENT_ID,
                     AZURE_AI_PROJECT_ENDPOINT, CONNECTION_MANAGER,
                     async_credential)
from .foundry_agent_factory import create_chat_agent_from_foundry

logger = logging.getLogger(__name__)


@AGENT_APP.conversation_update("membersAdded")
async def on_members_added(context: TurnContext, state: TurnState):  # noqa: ARG001
    conversation_id = context.activity.conversation.id
    user_id = (
        context.activity.from_property.id
        if context.activity.from_property
        else "unknown"
    )
    logger.info(
        "New connection established - Conversation ID: %s, "
        "User ID: %s, Activity ID: %s",
        conversation_id,
        user_id,
        context.activity.id
    )
    await context.send_activity(
        "Welcome to the Azure AI Foundry streaming sample. Ask any question "
        "and I'll stream the answer!"
    )


@AGENT_APP.activity("invoke")
async def invoke(context: TurnContext, state: TurnState):  # noqa: ARG001
    """
    Internal method to process template expansion or function invocation.
    """
    invoke_response = Activity(
        type=ActivityTypes.invoke_response,
        value={"status": 200}
    )
    logger.info(
        "Invoke activity received - ConvID=%s Type=%s ActID=%s",
        getattr(context.activity.conversation, "id", "unknown"),
        context.activity.type,
        context.activity.id,
    )
    await context.send_activity(invoke_response)


# In-memory storage for ChatAgent and AgentThread per conversation_id
# In production, use proper persistent storage

conversation_agents: dict[str, ChatAgent] = {}
conversation_threads: dict[str, AgentThread] = {}
# Store tool resources per conversation so we can pass them on each run
conversation_tool_resources: dict[str, object] = {}


@AGENT_APP.message(re.compile(r".+"))
async def on_user_message(context: TurnContext, state: TurnState):  # noqa: ARG001

    # The following attributes are provided dynamically by the SDK.
    context.streaming_response.set_feedback_loop(True)  # noqa: attr-defined
    context.streaming_response.set_generated_by_ai_label(True)  # noqa: attr-defined
    context.streaming_response.set_sensitivity_label(  # noqa: attr-defined
        SensitivityUsageInfo(
            type="https://schema.org/Message",
            schema_type="CreativeWork",
            name="Internal",
        )
    )
    context.streaming_response.queue_informative_update("Thinking...\n")  # noqa: attr-defined

    if not AZURE_AI_PROJECT_ENDPOINT or not AZURE_AI_FOUNDRY_AGENT_ID:
        context.streaming_response.queue_text_chunk(
            "Azure AI Agent client or agent ID not configured. Please check "
            "your environment variables."
        )
        await context.streaming_response.end_stream()
        return

    try:
        conversation_id = context.activity.conversation.id
        user_id = (
            context.activity.from_property.id
            if context.activity.from_property
            else "unknown"
        )
        activity_id = context.activity.id
        user_content = (
            context.activity.text.strip()
            if context.activity.text
            else ""
        )

        logger.info(
            "Message received - Conversation ID: %s, User ID: %s, "
            "Activity ID: %s, Message: '%s'",
            conversation_id,
            user_id,
            activity_id,
            (
                user_content[:100] + "..."
                if len(user_content) > 100
                else user_content
            )
        )
        if not user_content:
            context.streaming_response.queue_text_chunk(
                "Please enter a question to receive a streamed answer."
            )  # noqa: attr-defined
            await context.streaming_response.end_stream()  # noqa: attr-defined
            return

        agent = conversation_agents.get(conversation_id)
        thread = conversation_threads.get(conversation_id)
        if not agent:
            agent, tool_resources = await create_chat_agent_from_foundry(
                project_endpoint=AZURE_AI_PROJECT_ENDPOINT,
                agent_id=AZURE_AI_FOUNDRY_AGENT_ID,
                async_credential=async_credential,
            )
            if tool_resources is not None:
                conversation_tool_resources[conversation_id] = tool_resources
            conversation_agents[conversation_id] = agent
            logger.info(
                "Created new ChatAgent for conversation %s",
                conversation_id
            )
        else:
            logger.info(
                "Reusing ChatAgent for conversation %s",
                conversation_id
            )

        if not thread:
            # Create a new AgentThread for this conversation
            thread = agent.get_new_thread()
            conversation_threads[conversation_id] = thread
            thread_id = getattr(thread, 'id', 'unknown')
            logger.info(
                "Created new AgentThread - Conversation ID: %s, Thread ID: %s",
                conversation_id,
                thread_id
            )
        else:
            thread_id = getattr(thread, 'id', 'unknown')
            logger.info(
                "Reusing AgentThread - Conversation ID: %s, Thread ID: %s",
                conversation_id,
                thread_id
            )

        run_kwargs = {}
        tool_res = conversation_tool_resources.get(conversation_id)
        if tool_res is not None:
            run_kwargs["tool_resources"] = tool_res

        logger.info(
            "Starting agent run_stream - Conversation ID: %s, "
            "Thread ID: %s, Agent ID: %s",
            conversation_id,
            thread_id,
            AZURE_AI_FOUNDRY_AGENT_ID
        )

        chunk_count = 0
        run_id = None
        async for chunk in agent.run_stream(
            user_content, thread=thread, **run_kwargs
        ):
            # Try to extract run_id from the chunk if available
            if run_id is None and hasattr(chunk, 'run_id'):
                run_id = chunk.run_id
                logger.info(
                    "Agent run started - Conversation ID: %s, "
                    "Thread ID: %s, Run ID: %s",
                    conversation_id,
                    thread_id,
                    run_id
                )

            if chunk.text:
                chunk_count += 1
                context.streaming_response.queue_text_chunk(chunk.text)  # noqa: attr-defined

        logger.info(
            "Agent run completed - Conversation ID: %s, "
            "Thread ID: %s, Run ID: %s, Chunks: %d",
            conversation_id,
            thread_id,
            run_id or 'unknown',
            chunk_count
        )

    except Exception as exc:  # noqa: BLE001 - broad catch to surface to user
        logger.error(
            "Error during Agent Framework streaming - "
            "Conversation ID: %s, Error: %s",
            context.activity.conversation.id,
            exc,
            exc_info=True
        )
        context.streaming_response.queue_text_chunk(
            "An error occurred while generating the answer. "
            "Please try again later."
        )  # noqa: attr-defined
    finally:
        await context.streaming_response.end_stream()  # noqa: attr-defined
