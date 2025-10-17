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
    print(f"Invoke activity received: {context.activity}")
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
        user_content = context.activity.text.strip() if context.activity.text else ""
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
            logger.info("Created new ChatAgent for conversation %s", conversation_id)
        else:
            logger.info("Reusing ChatAgent for conversation %s", conversation_id)

        if not thread:
            # Create a new AgentThread for this conversation
            thread = agent.get_new_thread()
            conversation_threads[conversation_id] = thread
            logger.info(
                "Created new AgentThread for conversation %s", conversation_id
            )
        else:
            logger.info(
                "Reusing AgentThread for conversation %s", conversation_id
            )

        run_kwargs = {}
        tool_res = conversation_tool_resources.get(conversation_id)
        if tool_res is not None:
            run_kwargs["tool_resources"] = tool_res
        async for chunk in agent.run_stream(
            user_content, thread=thread, **run_kwargs
        ):
            if chunk.text:
                context.streaming_response.queue_text_chunk(chunk.text)  # noqa: attr-defined

    except Exception as exc:  # noqa: BLE001 - broad catch to surface to user
        logger.error(
            "Error during Agent Framework streaming: %s", exc
        )
        context.streaming_response.queue_text_chunk(
            "An error occurred while generating the answer. "
            "Please try again later."
        )  # noqa: attr-defined
    finally:
        await context.streaming_response.end_stream()  # noqa: attr-defined
