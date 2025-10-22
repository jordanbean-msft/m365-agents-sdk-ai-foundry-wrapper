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
from datetime import datetime, timezone

from microsoft_agents.activity import Activity, ActivityTypes, Attachment
from microsoft_agents.hosting.core import TurnContext, TurnState

from .config import (AGENT_APP, AZURE_AI_FOUNDRY_AGENT_ID,
                     AZURE_AI_PROJECT_ENDPOINT, CONVERSATION_TIMEOUT_SECONDS,
                     RESET_COMMAND_KEYWORDS, async_credential)
from .conversation_state import (conversation_agents,
                                 conversation_last_activity,
                                 conversation_threads,
                                 conversation_tool_resources,
                                 reset_conversation)
from .foundry_agent_factory import create_chat_agent_from_foundry

logger = logging.getLogger(__name__)


@AGENT_APP.conversation_update("membersAdded")
async def on_members_added(
    context: TurnContext, state: TurnState
):  # noqa: ARG001
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


def _build_reset_adaptive_card(title: str, message: str) -> dict:
    """Return a minimal Adaptive Card payload with a Restart button.

    The Restart button sends a message containing the first configured reset
    keyword (or 'reset' as a fallback) so command handling stays uniform.
    """
    reset_keyword = (
        RESET_COMMAND_KEYWORDS[0] if RESET_COMMAND_KEYWORDS else "reset"
    )
    return {
        "type": "message",
        "attachments": [
            {
                "contentType": "application/vnd.microsoft.card.adaptive",
                "content": {
                    "$schema": (
                        "http://adaptivecards.io/schemas/adaptive-card.json"
                    ),
                    "type": "AdaptiveCard",
                    "version": "1.5",
                    "body": [
                        {
                            "type": "TextBlock",
                            "size": "Medium",
                            "weight": "Bolder",
                            "text": title,
                        },
                        {
                            "type": "TextBlock",
                            "wrap": True,
                            "text": message,
                        },
                    ],
                    "actions": [
                        {
                            "type": "Action.Submit",
                            "title": "Restart Conversation",
                            "data": {
                                "msteams": {
                                    "type": "messageBack",
                                    "text": reset_keyword,
                                    "displayText": "Restart",
                                }
                            },
                        }
                    ],
                },
            }
        ],
    }


def _build_response_adaptive_card(markdown_text: str) -> dict:
    """Return an Adaptive Card payload with markdown response content.

    Renders the agent's response as a formatted markdown TextBlock.
    """
    return {
        "type": "message",
        "attachments": [
            {
                "contentType": "application/vnd.microsoft.card.adaptive",
                "content": {
                    "$schema": (
                        "http://adaptivecards.io/schemas/adaptive-card.json"
                    ),
                    "type": "AdaptiveCard",
                    "version": "1.5",
                    "body": [
                        {
                            "type": "TextBlock",
                            "text": markdown_text,
                            "wrap": True,
                        },
                    ],
                },
            }
        ],
    }


@AGENT_APP.message(re.compile(r".+"))
async def on_user_message(
    context: TurnContext, state: TurnState
):  # noqa: ARG001

    if not AZURE_AI_PROJECT_ENDPOINT or not AZURE_AI_FOUNDRY_AGENT_ID:
        await context.send_activity(
            "Azure AI Agent client or agent ID not configured. Please check "
            "your environment variables."
        )
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
            await context.send_activity(
                "Please enter a question to receive an answer."
            )
            return

        # --- Manual reset command detection (exact match) ---
        lowered = user_content.lower()
        if lowered in RESET_COMMAND_KEYWORDS:
            reset_conversation(conversation_id)
            await context.send_activity(
                "Conversation reset! Welcome back. "
                "Ask me anything to get started."
            )
            return

        # --- Timeout enforcement ---
        now = datetime.now(timezone.utc)
        last = conversation_last_activity.get(conversation_id)
        if (
            CONVERSATION_TIMEOUT_SECONDS > 0
            and last is not None
            and (now - last).total_seconds() > CONVERSATION_TIMEOUT_SECONDS
        ):
            reset_conversation(conversation_id)
            await context.send_activity(
                "Your session expired due to inactivity. Starting fresh!"
            )
            # We intentionally continue to process the *current* user message
            # as the first message of a fresh conversation (do not return).

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

        # Configure streaming response with labels and feedback
        context.streaming_response.set_feedback_loop(True)
        context.streaming_response.set_generated_by_ai_label(True)

        chunk_count = 0
        run_id = None
        full_response = []

        try:
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
                    full_response.append(chunk.text)
                    # Stream the chunk to the user
                    context.streaming_response.queue_text_chunk(chunk.text)
        except Exception as stream_error:
            logger.error(
                "Error during streaming - Conversation ID: %s, Error: %s",
                conversation_id,
                stream_error,
                exc_info=True
            )
            context.streaming_response.queue_text_chunk(
                "An error occurred while generating the response. "
                "Please try again."
            )
        finally:
            await context.streaming_response.end_stream()

        logger.info(
            "Agent run completed - Conversation ID: %s, "
            "Thread ID: %s, Run ID: %s, Chunks: %d",
            conversation_id,
            thread_id,
            run_id or 'unknown',
            chunk_count
        )

        # Replace streamed text with Adaptive Card containing markdown
        if full_response:
            response_text = "".join(full_response)
            card_dict = _build_response_adaptive_card(response_text)
            context.streaming_response.set_attachments(
                [
                    Attachment(
                        content_type="application/vnd.microsoft.card.adaptive",
                        content=card_dict["attachments"][0]["content"],
                    )
                ]
            )

        # Update last activity timestamp only after a successful run
        conversation_last_activity[conversation_id] = datetime.now(
            timezone.utc
        )

    except Exception as exc:  # noqa: BLE001 - broad catch to surface to user
        logger.error(
            "Error during Agent Framework - "
            "Conversation ID: %s, Error: %s",
            context.activity.conversation.id,
            exc,
            exc_info=True
        )
        await context.send_activity(
            "An error occurred while generating the answer. "
            "Please try again later."
        )
