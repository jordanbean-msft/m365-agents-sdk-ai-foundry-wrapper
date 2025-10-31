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
    markdown_text: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
    code_blocks: Optional[list] = None,
    images: Optional[list] = None,
) -> dict:
    body_elements = []

    # Add main text response
    if markdown_text:
        body_elements.append({
            "type": "TextBlock",
            "text": markdown_text,
            "wrap": True,
        })

    # Add code blocks
    if code_blocks:
        for code_block in code_blocks:
            body_elements.append({
                "type": "TextBlock",
                "text": f"```\n{code_block.get('code', '')}\n```",
                "wrap": True,
                "fontType": "Monospace",
                "separator": True,
            })

    # Add images
    if images:
        for img in images:
            # Note: file_id would need to be resolved to URL
            # For now, we'll add a placeholder
            body_elements.append({
                "type": "TextBlock",
                "text": f"[Image: {img.get('file_id')}]",
                "separator": True,
                "color": "Accent",
            })
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

        # Always show response time (or N/A)
        if response_time is not None:
            debug_items.append(f"{response_time:.0f}ms")
        else:
            debug_items.append("time: N/A")

        # Always show token info (or N/A)
        if total_tokens is not None:
            token_parts = [f"{total_tokens} tokens"]
            if prompt_tokens is not None:
                token_parts.append(f"prompt: {prompt_tokens}")
            if completion_tokens is not None:
                token_parts.append(f"completion: {completion_tokens}")
            debug_items.append(", ".join(token_parts))
        else:
            debug_items.append("tokens: N/A")

        if tool_calls:
            debug_items.append(f"tools: {', '.join(tool_calls)}")

        debug_text = " • ".join(debug_items)

        # Add thread ID and run ID on second line
        thread_info = thread_id or 'N/A'
        run_info = metadata.get('run_id') or 'N/A'
        debug_text += f"\nthread: {thread_info} | run: {run_info}"

        # Add debug info as always-visible, thin text block
        body_elements.append({
            "type": "TextBlock",
            "text": debug_text,
            "size": "Small",
            "color": "Accent",
            "wrap": True,
            "isSubtle": True,
            "separator": True,
            "spacing": "Small"
        })
    card_content = {
        "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
        "type": "AdaptiveCard",
        "version": "1.5",
        "body": body_elements,
    }
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
