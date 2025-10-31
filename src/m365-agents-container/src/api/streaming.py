"""Streaming helper utilities (Python SDK pass-through).

Implements the same high-level pattern as the C# `SapAgent` example using
the Python streaming response object directly. We DO NOT re-implement SDK
methods; we just call them:

    1. queue_informative_update -> status/progress messages
    2. queue_text_chunk -> incremental model output chunks
    3. set_attachments + end_stream -> final adaptive card message

Handlers can import these thin helpers for clarity. All exceptions are
swallowed (debug logged) because streaming clients may disconnect.
"""
from __future__ import annotations

import logging

from microsoft_agents.hosting.core import TurnContext

logger = logging.getLogger(__name__)


def queue_informative(context: TurnContext, message: str) -> None:
    """Queue an informative/status update (pass-through).

    Mirrors C# `QueueInformativeUpdateAsync`. Non-fatal on failure.
    """
    sr = getattr(context, "streaming_response", None)
    if not sr:
        logger.debug("No streaming_response; informative logged: %s", message)
        return
    if not message:
        return
    try:
        sr.queue_informative_update(message)
        logger.debug("Queued informative: %s", message)
    except (RuntimeError, OSError, ValueError) as exc:
        logger.debug(
            "Failed queue_informative '%s' (closed?): %s",
            message,
            exc,
        )


def queue_text(context: TurnContext, text: str) -> None:
    """Queue a text chunk (partial model output)."""
    sr = getattr(context, "streaming_response", None)
    if not sr or not text:
        if text:
            logger.debug(
                "No streaming_response; text chunk suppressed (%d chars)",
                len(text),
            )
        return
    try:
        sr.queue_text_chunk(text)
        logger.debug("Queued text chunk (%d chars)", len(text))
    except (RuntimeError, OSError, ValueError) as exc:
        logger.debug("Failed queue_text_chunk (closed?): %s", exc)


async def finalize_stream_with_card(
    context: TurnContext,
    card_dict: dict,
    *,
    enable_feedback_loop: bool = True,
) -> bool:
    """Attach final adaptive card and end stream.

    Returns True on streaming finalize success, else False (caller should
    fall back to normal send). `card_dict` is expected to be the dict
    returned by `build_response_adaptive_card` (message w/ attachments).
    """
    sr = getattr(context, "streaming_response", None)
    if not sr:
        logger.debug("No streaming_response; cannot finalize stream.")
        return False
    attachments = card_dict.get("attachments") if card_dict else None
    if not attachments:
        logger.debug("Card dict missing attachments; abort finalize.")
        return False
    try:
        sr.set_attachments(attachments)
    except (RuntimeError, OSError, ValueError) as exc:
        logger.debug("Failed set_attachments: %s", exc)
        return False
    if enable_feedback_loop:
        try:
            sr.set_feedback_loop(True)
            sr.set_feedback_loop_type("custom")
        except (RuntimeError, OSError, ValueError):
            pass
    try:
        await sr.end_stream()
        logger.debug("Stream finalized with adaptive card.")
        return True
    except (RuntimeError, OSError, ValueError) as exc:
        logger.debug("end_stream failed (fallback required): %s", exc)
        return False


# Backwards compatibility: old name used by handlers
def queue_status_update(context: TurnContext, message: str) -> None:
    """Legacy alias for queue_informative."""
    queue_informative(context, message)


__all__ = [
    "queue_informative",
    "queue_text",
    "finalize_stream_with_card",
    "queue_status_update",
]
