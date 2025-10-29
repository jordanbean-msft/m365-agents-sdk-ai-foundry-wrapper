"""Adaptive Card builders extracted from the legacy agent module."""
from __future__ import annotations

from typing import Any, Dict, Optional

from ..app.config import RESET_COMMAND_KEYWORDS


def build_reset_adaptive_card(title: str, message: str) -> dict:
    reset_keyword = RESET_COMMAND_KEYWORDS[0] if RESET_COMMAND_KEYWORDS else "reset"
    return {
        "type": "message",
        "attachments": [
            {
                "contentType": "application/vnd.microsoft.card.adaptive",
                "content": {
                    "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                    "type": "AdaptiveCard",
                    "version": "1.5",
                    "body": [
                        {"type": "TextBlock", "size": "Medium", "weight": "Bolder", "text": title},
                        {"type": "TextBlock", "wrap": True, "text": message},
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


def build_response_adaptive_card(
    markdown_text: str, metadata: Optional[Dict[str, Any]] = None
) -> dict:
    body_elements = [
        {
            "type": "TextBlock",
            "text": markdown_text,
            "wrap": True,
        },
    ]
    actions = []
    if metadata:
        # Extract values from metadata
        response_time = metadata.get("response_time_ms")
        total_tokens = metadata.get("total_tokens")
        prompt_tokens = metadata.get("prompt_tokens")
        completion_tokens = metadata.get("completion_tokens")
        tool_calls = metadata.get("tool_calls")
        thread_id = metadata.get("thread_id")

        # Format debug information for compact display
        debug_items = []
        if response_time is not None:
            debug_items.append(f"{response_time:.0f}ms")

        # Combine all token counts into single section
        if total_tokens is not None:
            token_parts = [f"{total_tokens} tokens"]
            if prompt_tokens is not None:
                token_parts.append(f"prompt: {prompt_tokens}")
            if completion_tokens is not None:
                token_parts.append(f"completion: {completion_tokens}")
            debug_items.append(", ".join(token_parts))

        if tool_calls:
            debug_items.append(f"tools: {', '.join(tool_calls)}")

        debug_text = " • ".join(debug_items)

        # Add thread ID on second line if available
        if thread_id:
            debug_text += f"\nthread: {thread_id}"

        body_elements.append({
            "type": "Container",
            "separator": True,
            "spacing": "Small",
            "items": [
                    {
                        "type": "Container",
                        "id": "debugInfoContainer",
                        "isVisible": False,
                        "items": [
                            {
                                "type": "TextBlock",
                                "text": debug_text,
                                "size": "Small",
                                "color": "Accent",
                                "wrap": True,
                                "isSubtle": True
                            }
                        ]
                    }
            ]
        })
        actions = [{
            "type": "Action.ToggleVisibility",
            "title": "Debug Info",
            "targetElements": ["debugInfoContainer"]
        }]
    card_content = {
        "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
        "type": "AdaptiveCard",
        "version": "1.5",
        "body": body_elements,
    }
    if actions:
        card_content["actions"] = actions
    return {
        "type": "message",
        "attachments": [
            {
                "contentType": "application/vnd.microsoft.card.adaptive",
                "content": card_content,
            }
        ],
    }


__all__ = ["build_reset_adaptive_card", "build_response_adaptive_card"]
