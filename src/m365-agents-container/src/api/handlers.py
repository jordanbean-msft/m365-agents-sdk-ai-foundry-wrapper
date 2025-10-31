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
    if not AZURE_AI_PROJECT_ENDPOINT or not AZURE_AI_FOUNDRY_AGENT_ID:
        await context.send_activity(
            (
                "Azure AI Agent client or agent ID not configured. "
                "Please check your environment variables."
            )
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
            context.activity.text.strip() if context.activity.text else ""
        )

        truncated_msg = (
            user_content[:100] + "..."
            if len(user_content) > 100
            else user_content
        )
        logger.info(
            (
                "Message received - Conversation ID: %s, User ID: %s, "
                "Activity ID: %s, Message: '%s'"
            ),
            conversation_id,
            user_id,
            activity_id,
            truncated_msg,
        )
        if not user_content:
            await context.send_activity(
                "Please enter a question to receive an answer."
            )
            return

        lowered = user_content.lower()
        if lowered in RESET_COMMAND_KEYWORDS:
            reset_conversation(conversation_id)
            await context.send_activity(
                (
                    "Conversation reset! Welcome back. Ask me anything to "
                    "get started."
                )
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
            (
                "Starting agent run_stream - Conversation ID: %s, "
                "Thread ID: %s, Agent ID: %s"
            ),
            conversation_id,
            thread_id,
            AZURE_AI_FOUNDRY_AGENT_ID,
        )

        # Initial informative update if streaming available
        queue_informative(context, "Starting agent run...")

        start_time = time.time()
        chunk_count = 0
        run_id = None
        code_blocks: List[Dict[str, Any]] = []
        images: List[Dict[str, Any]] = []
        total_tokens: Optional[int] = None
        prompt_tokens: Optional[int] = None
        completion_tokens: Optional[int] = None

        # (Already queued above before entering try loop)

        try:
            # Run the agent stream
            async for chunk in agent.run_stream(
                user_content, thread=thread, **run_kwargs
            ):
                # Increment chunk count for received update
                chunk_count += 1

                if run_id is None and getattr(chunk, "response_id", None):
                    run_id = chunk.response_id
                    logger.info(
                        "Run started - ConvID:%s Thread:%s Run:%s",
                        conversation_id,
                        thread_id,
                        run_id,
                    )

                if hasattr(chunk, "contents") and chunk.contents:
                    for content in chunk.contents:
                        ctype = type(content).__name__

                        # Handle code content (from code_interpreter)
                        if "Code" in ctype:
                            code_text = getattr(
                                content, "code", None
                            ) or getattr(content, "text", None)
                            if code_text:
                                code_blocks.append(
                                    {"code": code_text, "type": ctype}
                                )
                                logger.info("Code block detected: %s", ctype)

                        # Handle image content
                        elif "Image" in ctype or "ImageFile" in ctype:
                            image_file_id = getattr(content, "file_id", None)
                            if image_file_id:
                                images.append(
                                    {"file_id": image_file_id, "type": ctype}
                                )
                                logger.info(
                                    "Image detected: file_id=%s", image_file_id
                                )

                        elif ctype == "UsageContent":
                            # Extract token counts from details object
                            if hasattr(content, "details"):
                                details = getattr(content, "details", None)
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
                if getattr(chunk, "text", None):
                    # Stream text immediately (don't collect for card)
                    queue_text(context, chunk.text)
        except json.JSONDecodeError as json_error:
            logger.error(
                (
                    "JSON decode error (likely 408 timeout from AI Foundry) - "
                    "Conversation ID: %s, Error: %s"
                ),
                conversation_id,
                json_error,
                exc_info=True,
            )
            await context.send_activity(
                (
                    "The request timed out while waiting for the agent to "
                    "respond. This may be due to a long-running operation. "
                    "Please try again with a simpler query."
                )
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
                (
                    "An error occurred while generating the response. "
                    "Please try again."
                )
            )
            return

        response_time_ms = (time.time() - start_time) * 1000
        if thread and hasattr(thread, "service_thread_id"):
            thread_id = thread.service_thread_id
            logger.info("Extracted thread.service_thread_id: %s", thread_id)

        logger.info(
            (
                "Agent run completed - Conversation ID: %s, Thread ID: %s, "
                "Run ID: %s, Chunks: %d, Response Time: %.0f ms, Tokens: %s"
            ),
            conversation_id,
            thread_id,
            run_id or "unknown",
            chunk_count,
            response_time_ms,
            total_tokens or "N/A",
        )

        logger.debug("Formatting final response payload")

        # Only send adaptive card if there's non-text content to display
        if code_blocks or images:
            metadata = None
            if ENABLE_RESPONSE_METADATA_CARD:
                metadata = {
                    "response_time_ms": response_time_ms,
                    "thread_id": thread_id,
                    "agent_id": AZURE_AI_FOUNDRY_AGENT_ID,
                    "run_id": run_id,
                    "total_tokens": total_tokens,
                    "prompt_tokens": prompt_tokens,
                    "completion_tokens": completion_tokens,
                }
            else:
                logger.debug(
                    "Metadata card feature disabled; omitting metadata section"
                )
            # Pass empty string for text since it was already streamed
            card_dict = build_response_adaptive_card(
                "", metadata, code_blocks, images
            )
            # Attempt streaming finalize with helper; fallback if unsuccessful.
            streamed = await finalize_stream_with_card(context, card_dict)
            if streamed:
                return

            # Fallback: send adaptive card as normal activity.
            card_attachment = Attachment(
                content_type="application/vnd.microsoft.card.adaptive",
                content=card_dict["attachments"][0]["content"],
            )
            sender_final = getattr(
                context.activity, "from_property", None
            ) or getattr(context.activity, "recipient", None)
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
            # Text already streamed; optional metadata card.
            if ENABLE_RESPONSE_METADATA_CARD:
                logger.debug(
                    "Building metadata card (flag enabled, no code/images)"
                )
                metadata = {
                    "agent_id": AZURE_AI_FOUNDRY_AGENT_ID,
                    "thread_id": thread_id,
                    "run_id": run_id,
                    "response_time_ms": response_time_ms,
                    "total_tokens": total_tokens,
                    "prompt_tokens": prompt_tokens,
                    "completion_tokens": completion_tokens,
                }
                logger.debug(
                    (
                        "Metrics rt=%s tot=%s prm=%s cmp=%s "
                        "thread=%s run=%s"
                    ),
                    response_time_ms,
                    total_tokens,
                    prompt_tokens,
                    completion_tokens,
                    thread_id,
                    run_id,
                )
                card_dict = build_response_adaptive_card(
                    markdown_text=None,
                    metadata=metadata,
                    code_blocks=None,
                    images=None,
                )
                adaptive_content = card_dict["attachments"][0]["content"]
                body_count = (
                    len(adaptive_content.get("body", []))
                    if isinstance(adaptive_content, dict)
                    else "unknown"
                )
                logger.debug(
                    "Metadata card body elements count: %s",
                    body_count,
                )
                card_attachment = Attachment(
                    content_type="application/vnd.microsoft.card.adaptive",
                    content=adaptive_content,
                )
                sr = getattr(context, "streaming_response", None)
                if sr:
                    try:
                        sr.set_attachments([card_attachment])
                        await sr.end_stream()
                        logger.debug("Stream ended with metadata card")
                    except (RuntimeError, OSError, ValueError) as exc:
                        logger.debug("Failed to end stream: %s", exc)
                else:
                    sender_final = getattr(
                        context.activity, "from_property", None
                    ) or getattr(context.activity, "recipient", None)
                    await context.send_activity(
                        Activity(
                            **{
                                "type": ActivityTypes.message,
                                "attachments": [card_attachment],
                                **(
                                    {"from": sender_final}
                                    if sender_final
                                    else {}
                                ),
                            }
                        )
                    )
            else:
                logger.debug("Metadata card disabled; ending stream")
                sr = getattr(context, "streaming_response", None)
                if sr:
                    try:
                        await sr.end_stream()
                    except (RuntimeError, OSError, ValueError) as exc:
                        logger.debug(
                            "Failed to end stream (no metadata): %s", exc
                        )

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
