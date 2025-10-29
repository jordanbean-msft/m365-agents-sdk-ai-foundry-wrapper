"""Streaming status helper utilities."""
from __future__ import annotations

import logging

from microsoft_agents.hosting.core import TurnContext

logger = logging.getLogger(__name__)


def queue_status_update(context: TurnContext, message: str) -> None:
    """Best-effort queue of a streaming status update.

    Swallows exceptions caused by disconnected streaming clients.
    """
    if hasattr(context, "streaming_response") and context.streaming_response:
        try:
            context.streaming_response.queue_informative_update(message)
            logger.debug("Queued streaming status: %s", message)
        except Exception as exc:  # noqa: BLE001
            logger.debug(
                "Failed to queue streaming status '%s' (likely closed): %s",
                message,
                exc,
            )
    else:
        logger.debug("Streaming not available, status logged only: %s", message)


__all__ = ["queue_status_update"]
