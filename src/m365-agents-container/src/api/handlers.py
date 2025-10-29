"""Bot activity handlers (refactored from legacy agent.py)."""
from __future__ import annotations

import logging
import re
import time
from typing import Any, Dict, List, Optional

from azure.identity.aio import DefaultAzureCredential
from microsoft_agents.activity import Activity, ActivityTypes, Attachment
from microsoft_agents.hosting.core import TurnContext, TurnState

from ..agents import (conversation_threads, conversation_tool_resources,
                      create_chat_agent_from_foundry, reset_conversation)
from ..app.config import (AGENT_APP, AZURE_AI_FOUNDRY_AGENT_ID,
                          AZURE_AI_PROJECT_ENDPOINT, RESET_COMMAND_KEYWORDS)
from .cards import build_response_adaptive_card
from .streaming import queue_status_update

logger = logging.getLogger(__name__)


@AGENT_APP.conversation_update("membersAdded")
async def on_members_added(context: TurnContext, state: TurnState):  # noqa: ARG001
    conversation_id = context.activity.conversation.id
    user_id = (
        context.activity.from_property.id if context.activity.from_property else "unknown"
    )
    logger.info(
        "New connection established - Conversation ID: %s, User ID: %s, Activity ID: %s",
        conversation_id,
        user_id,
        context.activity.id,
    )
    await context.send_activity(
        "Welcome to the Azure AI Foundry streaming sample. Ask any question and I'll stream the answer!"
    )


@AGENT_APP.activity("invoke")
async def invoke(context: TurnContext, state: TurnState):  # noqa: ARG001
    sender = getattr(context.activity, "from_property", None) or getattr(
        context.activity, "recipient", None
    )
    invoke_response = Activity(
        **{
            "type": ActivityTypes.invoke_response,
            "value": {"status": 200},
            **({"from": sender} if sender else {}),
        }
    )
    logger.info(
        "Invoke activity received - ConvID=%s Type=%s ActID=%s",
        getattr(context.activity.conversation, "id", "unknown"),
        context.activity.type,
        context.activity.id,
    )
    await context.send_activity(invoke_response)


@AGENT_APP.message(re.compile(r".+"))
async def on_user_message(context: TurnContext, state: TurnState):  # noqa: ARG001
    if not AZURE_AI_PROJECT_ENDPOINT or not AZURE_AI_FOUNDRY_AGENT_ID:
        await context.send_activity(
            "Azure AI Agent client or agent ID not configured. Please check your environment variables."
        )
        return

    try:
        conversation_id = context.activity.conversation.id
        user_id = (
            context.activity.from_property.id if context.activity.from_property else "unknown"
        )
        activity_id = context.activity.id
        user_content = context.activity.text.strip() if context.activity.text else ""

        logger.info(
            "Message received - Conversation ID: %s, User ID: %s, Activity ID: %s, Message: '%s'",
            conversation_id,
            user_id,
            activity_id,
            (user_content[:100] + "..." if len(user_content) > 100 else user_content),
        )
        if not user_content:
            await context.send_activity("Please enter a question to receive an answer.")
            return

        lowered = user_content.lower()
        if lowered in RESET_COMMAND_KEYWORDS:
            reset_conversation(conversation_id)
            await context.send_activity(
                "Conversation reset! Welcome back. Ask me anything to get started."
            )
            return

        # Always create fresh agent with new credentials to avoid
        # token expiration (credentials expire after ~1 hour).
        # Create fresh credential instance per request to ensure
        # tokens are not cached and can be refreshed.
        fresh_credential = DefaultAzureCredential()
        agent, tool_resources = await create_chat_agent_from_foundry(
            project_endpoint=AZURE_AI_PROJECT_ENDPOINT,
            agent_id=AZURE_AI_FOUNDRY_AGENT_ID,
            async_credential=fresh_credential,
        )
        if tool_resources is not None:
            conversation_tool_resources[conversation_id] = tool_resources
        logger.info(
            "Created ChatAgent with fresh credentials for conversation %s",
            conversation_id,
        )

        # Reuse thread if it exists (threads don't hold auth tokens)
        thread = conversation_threads.get(conversation_id)
        if not thread:
            thread = agent.get_new_thread()
            conversation_threads[conversation_id] = thread
            thread_id = getattr(thread, "id", "unknown")
            logger.info(
                "Created new AgentThread - Conversation ID: %s, Thread ID: %s",
                conversation_id,
                thread_id,
            )
        else:
            thread_id = getattr(thread, "id", "unknown")
            logger.info(
                "Reusing AgentThread - Conversation ID: %s, Thread ID: %s",
                conversation_id,
                thread_id,
            )

        run_kwargs: Dict[str, Any] = {}
        tool_res = conversation_tool_resources.get(conversation_id)
        if tool_res is not None:
            run_kwargs["tool_resources"] = tool_res

        logger.info(
            "Starting agent run_stream - Conversation ID: %s, Thread ID: %s, Agent ID: %s",
            conversation_id,
            thread_id,
            AZURE_AI_FOUNDRY_AGENT_ID,
        )

        # If streaming is enabled we suppress textual token streaming to avoid duplicate
        # final content (user wants only the adaptive card). We monkey patch queue_text_chunk
        # and queueTextChunk to no-op while leaving informative updates intact.
        if hasattr(context, "streaming_response") and context.streaming_response:
            sr = context.streaming_response
            for attr in ["queue_text_chunk", "queueTextChunk"]:
                if hasattr(sr, attr):
                    original = getattr(sr, attr)
                    if callable(original):
                        try:
                            setattr(sr, attr, lambda *a, **kw: None)
                            logger.debug("Suppressed streaming text via monkey patch: %s", attr)
                        except Exception as patch_exc:  # noqa: BLE001
                            logger.debug("Failed monkey patching %s: %s", attr, patch_exc)

        start_time = time.time()
        chunk_count = 0
        run_id = None
        full_response: List[str] = []
        total_tokens: Optional[int] = None
        prompt_tokens: Optional[int] = None
        completion_tokens: Optional[int] = None
        tool_calls: List[str] = []

        queue_status_update(context, "Starting agent run...")

        try:
            async for chunk in agent.run_stream(user_content, thread=thread, **run_kwargs):
                chunk_type = type(chunk).__name__
                logger.debug(
                    "Chunk %d type: %s, has contents: %s",
                    chunk_count + 1,
                    chunk_type,
                    hasattr(chunk, "contents") and chunk.contents is not None,
                )

                if run_id is None and getattr(chunk, "response_id", None):
                    run_id = chunk.response_id
                    logger.info(
                        "Agent run started - Conversation ID: %s, Thread ID: %s, Run ID: %s",
                        conversation_id,
                        thread_id,
                        run_id,
                    )

                if hasattr(chunk, "contents") and chunk.contents:
                    for content in chunk.contents:
                        ctype = type(content).__name__
                        logger.debug("Content type: %s", ctype)
                        if ctype == "UsageContent":
                            # Extract token counts from details object
                            if hasattr(content, "details"):
                                details = content.details
                                extracted_map = {
                                    "total_tokens": getattr(
                                        details, "total_token_count", None
                                    ),
                                    "prompt_tokens": getattr(
                                        details, "input_token_count", None
                                    ),
                                    "completion_tokens": getattr(
                                        details, "output_token_count", None
                                    ),
                                }
                                if (
                                    prompt_tokens is None
                                    and extracted_map["prompt_tokens"]
                                    is not None
                                ):
                                    prompt_tokens = extracted_map[
                                        "prompt_tokens"
                                    ]
                                if (
                                    completion_tokens is None
                                    and extracted_map["completion_tokens"]
                                    is not None
                                ):
                                    completion_tokens = extracted_map[
                                        "completion_tokens"
                                    ]
                                if (
                                    total_tokens is None
                                    and extracted_map["total_tokens"]
                                    is not None
                                ):
                                    total_tokens = extracted_map[
                                        "total_tokens"
                                    ]
                                # Fallback calculation
                                if (
                                    total_tokens is None
                                    and prompt_tokens is not None
                                    and completion_tokens is not None
                                ):
                                    total_tokens = (
                                        prompt_tokens + completion_tokens
                                    )
                        if "Tool" in ctype or "Function" in ctype:
                            tool_name = getattr(content, "name", str(content))
                            if tool_name and tool_name not in tool_calls:
                                tool_calls.append(tool_name)
                                logger.info("Tool call detected: %s", tool_name)
                                queue_status_update(context, f"Using tool: {tool_name}...")
                if getattr(chunk, "text", None):
                    chunk_count += 1
                    full_response.append(chunk.text)
        except Exception as stream_error:  # noqa: BLE001
            logger.error(
                "Error during agent run - Conversation ID: %s, Error: %s",
                conversation_id,
                stream_error,
                exc_info=True,
            )
            await context.send_activity(
                "An error occurred while generating the response. Please try again."
            )
            return

        response_time_ms = (time.time() - start_time) * 1000
        if thread and hasattr(thread, "service_thread_id"):
            thread_id = thread.service_thread_id
            logger.info("Extracted thread.service_thread_id: %s", thread_id)

        logger.info(
            "Agent run completed - Conversation ID: %s, Thread ID: %s, Run ID: %s, Chunks: %d, Response Time: %.0f ms, Tokens: %s",
            conversation_id,
            thread_id,
            run_id or "unknown",
            chunk_count,
            response_time_ms,
            total_tokens or "N/A",
        )

        logger.debug("Formatting final response payload")

        if full_response:
            response_text = "".join(full_response)

            # Log token information for debugging
            logger.info(
                "Token usage - Total: %s, Prompt: %s, Completion: %s",
                total_tokens,
                prompt_tokens,
                completion_tokens,
            )

            metadata = {
                "response_time_ms": response_time_ms,
                "thread_id": thread_id,
                "agent_id": AZURE_AI_FOUNDRY_AGENT_ID,
                "run_id": run_id,
                "total_tokens": total_tokens,
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "tool_calls": tool_calls if tool_calls else None,
            }
            card_dict = build_response_adaptive_card(response_text, metadata)
            card_attachment = Attachment(
                content_type="application/vnd.microsoft.card.adaptive",
                content=card_dict["attachments"][0]["content"],
            )

            # Preferred path: use streaming completion so initial status messages clear.
            # Per Microsoft docs: Only set attachments, do NOT set any final text to avoid placeholder.
            # The SDK will send the card-only message when end_stream() is called.
            if hasattr(context, "streaming_response") and context.streaming_response:
                sr = context.streaming_response
                # Attach adaptive card (only allowed on final chunk per docs)
                try:
                    sr.set_attachments([card_attachment])
                except Exception as exc:  # noqa: BLE001
                    logger.debug("Failed to set attachments on streaming_response: %s", exc)
                # Enable feedback loop labeling
                try:
                    sr.set_feedback_loop(True)
                    sr.set_feedback_loop_type("custom")
                except Exception as exc:  # noqa: BLE001
                    logger.debug("Failed to set feedback loop properties: %s", exc)
                # End the stream (sends final message with card only, no text). If this fails fall back to normal activity send.
                try:
                    await sr.end_stream()
                    return
                except Exception as exc:  # noqa: BLE001
                    logger.warning(
                        "Streaming end failed; falling back to normal activity delivery: %s", exc)
            # Fallback: send final adaptive card as normal activity
            sender_final = getattr(context.activity, "from_property", None) or getattr(
                context.activity, "recipient", None
            )
            final_activity = Activity(
                **{
                    "type": ActivityTypes.message,
                    "attachments": [card_attachment],
                    "entities": [
                        {
                            "type": "https://schema.org/Message",
                            "@type": "Message",
                            "@context": "https://schema.org",
                            "additionalType": ["AIGeneratedContent"],
                        }
                    ],
                    "channel_data": {"feedbackLoop": {"type": "custom"}},
                    **({"from": sender_final} if sender_final else {}),
                }
            )
            await context.send_activity(final_activity)
        else:
            await context.send_activity(
                "I received your message but didn't generate a response. "
                "Please try again."
            )
    except Exception as exc:  # noqa: BLE001
        logger.error(
            "Error during Agent Framework - Conversation ID: %s, Error: %s",
            context.activity.conversation.id,
            exc,
            exc_info=True,
        )
        await context.send_activity(
            "An error occurred while generating the answer. "
            "Please try again later."
        )
