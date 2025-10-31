"""Bot activity handlers (refactored from legacy agent.py)."""
from __future__ import annotations

import json
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
                          AZURE_AI_PROJECT_ENDPOINT,
                          ENABLE_RESPONSE_METADATA_CARD,
                          RESET_COMMAND_KEYWORDS)
from .cards import build_response_adaptive_card
from .streaming import finalize_stream_with_card, queue_informative, queue_text

logger = logging.getLogger(__name__)


def _validate_configuration() -> bool:
    """Check if required Azure AI configuration is present."""
    return bool(AZURE_AI_PROJECT_ENDPOINT and AZURE_AI_FOUNDRY_AGENT_ID)


def _extract_conversation_context(context: TurnContext) -> Dict[str, str]:
    """Extract conversation metadata from Bot Framework activity."""
    activity_id = context.activity.id or "unknown"
    return {
        "conversation_id": context.activity.conversation.id,
        "user_id": (
            context.activity.from_property.id
            if context.activity.from_property
            else "unknown"
        ),
        "activity_id": activity_id,
        "user_content": (
            context.activity.text.strip() if context.activity.text else ""
        ),
    }


async def _handle_reset_command(
    context: TurnContext, conversation_id: str
) -> None:
    """Reset conversation state and notify user."""
    reset_conversation(conversation_id)
    await context.send_activity(
        "Conversation reset! Welcome back. Ask me anything to get started."
    )


async def _create_agent_and_thread(
    conversation_id: str,
) -> tuple[Any, Any, str]:
    """Create or reuse agent and conversation thread.

    Returns:
        Tuple of (agent, thread, thread_id)
    """
    # Always create fresh credentials to avoid token expiration
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

    # Reuse thread if it exists
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

    return agent, thread, thread_id


def _process_chunk_content(
    chunk: Any,
    code_blocks: List[Dict[str, Any]],
    images: List[Dict[str, Any]],
    token_counts: Dict[str, Optional[int]],
) -> None:
    """Process content from a single agent stream chunk.

    Extracts code blocks, images, and token usage information.
    """
    if not hasattr(chunk, "contents") or not chunk.contents:
        return

    for content in chunk.contents:
        ctype = type(content).__name__

        # Handle code content
        if "Code" in ctype:
            code_text = getattr(content, "code", None) or getattr(
                content, "text", None
            )
            if code_text:
                code_blocks.append({"code": code_text, "type": ctype})
                logger.info("Code block detected: %s", ctype)

        # Handle image content
        elif "Image" in ctype or "ImageFile" in ctype:
            image_file_id = getattr(content, "file_id", None)
            if image_file_id:
                images.append({"file_id": image_file_id, "type": ctype})
                logger.info("Image detected: file_id=%s", image_file_id)

        # Handle usage/token information
        elif ctype == "UsageContent":
            _extract_token_counts(content, token_counts)


def _extract_token_counts(
    content: Any, token_counts: Dict[str, Optional[int]]
) -> None:
    """Extract token usage metrics from UsageContent."""
    if not hasattr(content, "details"):
        return

    details = getattr(content, "details", None)
    if not details:
        return

    # Extract individual token counts
    if token_counts["prompt_tokens"] is None:
        token_counts["prompt_tokens"] = getattr(
            details, "input_token_count", None
        )
    if token_counts["completion_tokens"] is None:
        token_counts["completion_tokens"] = getattr(
            details, "output_token_count", None
        )
    if token_counts["total_tokens"] is None:
        token_counts["total_tokens"] = getattr(
            details, "total_token_count", None
        )

    # Fallback calculation
    if (
        token_counts["total_tokens"] is None
        and token_counts["prompt_tokens"] is not None
        and token_counts["completion_tokens"] is not None
    ):
        token_counts["total_tokens"] = (
            token_counts["prompt_tokens"]
            + token_counts["completion_tokens"]
        )


async def _stream_agent_response(
    agent: Any,
    user_content: str,
    thread: Any,
    conversation_id: str,
    context: TurnContext,
) -> Dict[str, Any]:
    """Stream agent response and collect metadata.

    Returns:
        Dictionary containing run metadata and collected content.
    """
    run_kwargs: Dict[str, Any] = {}
    tool_res = conversation_tool_resources.get(conversation_id)
    if tool_res is not None:
        run_kwargs["tool_resources"] = tool_res

    thread_id = getattr(thread, "id", "unknown")
    logger.info(
        "Starting agent run_stream - Conversation ID: %s, "
        "Thread ID: %s, Agent ID: %s",
        conversation_id,
        thread_id,
        AZURE_AI_FOUNDRY_AGENT_ID,
    )

    queue_informative(context, "Starting agent run...")

    start_time = time.time()
    chunk_count = 0
    run_id = None
    code_blocks: List[Dict[str, Any]] = []
    images: List[Dict[str, Any]] = []
    token_counts: Dict[str, Optional[int]] = {
        "total_tokens": None,
        "prompt_tokens": None,
        "completion_tokens": None,
    }

    async for chunk in agent.run_stream(
        user_content, thread=thread, **run_kwargs
    ):
        chunk_count += 1

        if run_id is None and getattr(chunk, "response_id", None):
            run_id = chunk.response_id
            logger.info(
                "Run started - ConvID:%s Thread:%s Run:%s",
                conversation_id,
                thread_id,
                run_id,
            )

        _process_chunk_content(chunk, code_blocks, images, token_counts)

        if getattr(chunk, "text", None):
            queue_text(context, chunk.text)

    response_time_ms = (time.time() - start_time) * 1000

    # Update thread_id if service_thread_id is available
    if thread and hasattr(thread, "service_thread_id"):
        thread_id = thread.service_thread_id

    logger.info(
        "Agent run completed - Conversation ID: %s, Thread ID: %s, "
        "Run ID: %s, Chunks: %d, Response Time: %.0f ms, Tokens: %s",
        conversation_id,
        thread_id,
        run_id or "unknown",
        chunk_count,
        response_time_ms,
        token_counts["total_tokens"] or "N/A",
    )

    return {
        "run_id": run_id,
        "thread_id": thread_id,
        "response_time_ms": response_time_ms,
        "code_blocks": code_blocks,
        "images": images,
        **token_counts,
    }


async def _send_content_card(
    context: TurnContext,
    code_blocks: List[Dict[str, Any]],
    images: List[Dict[str, Any]],
    run_metadata: Dict[str, Any],
) -> None:
    """Send adaptive card with code blocks and/or images."""
    metadata = None
    if ENABLE_RESPONSE_METADATA_CARD:
        metadata = {
            "response_time_ms": run_metadata["response_time_ms"],
            "thread_id": run_metadata["thread_id"],
            "agent_id": AZURE_AI_FOUNDRY_AGENT_ID,
            "run_id": run_metadata["run_id"],
            "total_tokens": run_metadata["total_tokens"],
            "prompt_tokens": run_metadata["prompt_tokens"],
            "completion_tokens": run_metadata["completion_tokens"],
        }

    # Text was already streamed, pass empty string
    card_dict = build_response_adaptive_card(
        "", metadata, code_blocks, images
    )

    # Try streaming finalize first
    streamed = await finalize_stream_with_card(context, card_dict)
    if streamed:
        return

    # Fallback to normal activity
    card_attachment = Attachment(
        content_type="application/vnd.microsoft.card.adaptive",
        content=card_dict["attachments"][0]["content"],
    )
    sender = getattr(context.activity, "from_property", None) or getattr(
        context.activity, "recipient", None
    )
    await context.send_activity(
        Activity(
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
                **({"from": sender} if sender else {}),
            }
        )
    )


async def _send_metadata_card(
    context: TurnContext, run_metadata: Dict[str, Any]
) -> None:
    """Send metadata-only adaptive card."""
    metadata = {
        "agent_id": AZURE_AI_FOUNDRY_AGENT_ID,
        "thread_id": run_metadata["thread_id"],
        "run_id": run_metadata["run_id"],
        "response_time_ms": run_metadata["response_time_ms"],
        "total_tokens": run_metadata["total_tokens"],
        "prompt_tokens": run_metadata["prompt_tokens"],
        "completion_tokens": run_metadata["completion_tokens"],
    }

    logger.debug(
        "Metrics rt=%s tot=%s prm=%s cmp=%s thread=%s run=%s",
        run_metadata["response_time_ms"],
        run_metadata["total_tokens"],
        run_metadata["prompt_tokens"],
        run_metadata["completion_tokens"],
        run_metadata["thread_id"],
        run_metadata["run_id"],
    )

    card_dict = build_response_adaptive_card(
        markdown_text=None,
        metadata=metadata,
        code_blocks=None,
        images=None,
    )

    card_attachment = Attachment(
        content_type="application/vnd.microsoft.card.adaptive",
        content=card_dict["attachments"][0]["content"],
    )

    sr = getattr(context, "streaming_response", None)
    if sr:
        try:
            sr.set_attachments([card_attachment])
            await sr.end_stream()
            logger.debug("Stream ended with metadata card")
            return
        except (RuntimeError, OSError, ValueError) as exc:
            logger.debug("Failed to end stream: %s", exc)

    # Fallback to normal activity
    sender = getattr(context.activity, "from_property", None) or getattr(
        context.activity, "recipient", None
    )
    await context.send_activity(
        Activity(
            **{
                "type": ActivityTypes.message,
                "attachments": [card_attachment],
                **({"from": sender} if sender else {}),
            }
        )
    )


@AGENT_APP.activity("invoke")
async def invoke(
    context: TurnContext, state: TurnState
):  # noqa: ARG001
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
async def on_user_message(
    context: TurnContext, state: TurnState
):  # noqa: ARG001
    """Handle incoming user messages and orchestrate agent interaction."""
    # Validate configuration
    if not _validate_configuration():
        await context.send_activity(
            "Azure AI Agent client or agent ID not configured. "
            "Please check your environment variables."
        )
        return

    try:
        # Extract conversation context
        conv_ctx = _extract_conversation_context(context)
        conversation_id = conv_ctx["conversation_id"]
        user_content = conv_ctx["user_content"]

        # Log incoming message
        truncated_msg = user_content[:100] + "..." if len(
            user_content
        ) > 100 else user_content
        logger.info(
            "Message received - Conversation ID: %s, User ID: %s, "
            "Activity ID: %s, Message: '%s'",
            conversation_id,
            conv_ctx["user_id"],
            conv_ctx["activity_id"],
            truncated_msg,
        )

        # Validate user input
        if not user_content:
            await context.send_activity(
                "Please enter a question to receive an answer."
            )
            return

        # Handle reset command
        if user_content.lower() in RESET_COMMAND_KEYWORDS:
            await _handle_reset_command(context, conversation_id)
            return

        # Create/retrieve agent and thread
        agent, thread, thread_id = await _create_agent_and_thread(
            conversation_id
        )

        # Stream agent response and collect metadata
        try:
            run_metadata = await _stream_agent_response(
                agent, user_content, thread, conversation_id, context
            )
        except json.JSONDecodeError as json_error:
            logger.error(
                "JSON decode error (likely 408 timeout from AI Foundry) - "
                "Conversation ID: %s, Error: %s",
                conversation_id,
                json_error,
                exc_info=True,
            )
            await context.send_activity(
                "The request timed out while waiting for the agent to "
                "respond. This may be due to a long-running operation. "
                "Please try again with a simpler query."
            )
            return
        except Exception as stream_error:  # noqa: BLE001
            logger.error(
                "Error during agent run - Conversation ID: %s, Error: %s",
                conversation_id,
                stream_error,
                exc_info=True,
            )
            await context.send_activity(
                "An error occurred while generating the response. "
                "Please try again."
            )
            return

        # Send appropriate response card(s)
        if run_metadata["code_blocks"] or run_metadata["images"]:
            # Send card with code/images
            await _send_content_card(
                context,
                run_metadata["code_blocks"],
                run_metadata["images"],
                run_metadata,
            )
        elif ENABLE_RESPONSE_METADATA_CARD:
            # Send metadata-only card
            await _send_metadata_card(context, run_metadata)
        else:
            # Just end the stream (text already sent)
            logger.debug("Metadata card disabled; ending stream")
            sr = getattr(context, "streaming_response", None)
            if sr:
                try:
                    await sr.end_stream()
                except (RuntimeError, OSError, ValueError) as exc:
                    logger.debug("Failed to end stream (no metadata): %s", exc)

    except Exception as exc:  # noqa: BLE001
        logger.error(
            "Unhandled error in on_user_message: %s", exc, exc_info=True
        )
        try:
            await context.send_activity(
                "An unexpected error occurred. Please try again."
            )
        except Exception:  # noqa: BLE001
            logger.debug("Failed to send error activity")
