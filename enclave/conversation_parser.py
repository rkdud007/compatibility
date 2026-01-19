"""Parser for ChatGPT export format.

ChatGPT exports conversations in a nested mapping structure.
This module extracts simple {role, content} messages from that format.
"""

import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


def extract_messages_from_chatgpt_export(conversations: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    """Extract messages from ChatGPT export format.

    Handles two formats:
    1. Raw ChatGPT export: [{"mapping": {...}, "title": "..."}]
    2. Pre-processed format: [{"role": "user", "content": "..."}]

    Args:
        conversations: List of conversations (either format).

    Returns:
        List of {role, content} dicts.
    """
    # Check if already in simple format.
    if conversations and "role" in conversations[0] and "content" in conversations[0]:
        logger.debug("Conversations already in simple format")
        return conversations

    # Parse ChatGPT export format.
    logger.debug(f"Parsing {len(conversations)} ChatGPT conversations")
    all_messages = []

    for conv in conversations:
        messages = _extract_messages_from_conversation(conv)
        all_messages.extend(messages)

    logger.debug(f"Extracted {len(all_messages)} messages total")
    return all_messages


def _extract_messages_from_conversation(conversation: Dict[str, Any]) -> List[Dict[str, str]]:
    """Extract messages from a single ChatGPT conversation.

    Args:
        conversation: Single conversation from ChatGPT export.

    Returns:
        List of {role, content} dicts.
    """
    messages = []
    mapping = conversation.get("mapping", {})

    if not mapping:
        logger.warning("Conversation has no mapping field")
        return messages

    # ChatGPT export uses a tree structure.
    # We traverse it to extract messages.
    for node_id, node_data in mapping.items():
        message = node_data.get("message")
        if not message:
            continue

        # Extract role.
        author = message.get("author", {})
        role = author.get("role", "")

        # Only keep user and assistant messages.
        if role not in ["user", "assistant"]:
            continue

        # Extract content.
        content_obj = message.get("content", {})
        parts = content_obj.get("parts", [])

        # Join all parts into a single string.
        if parts and isinstance(parts, list):
            content = "\n".join(str(part) for part in parts if part)

            # Only add if there's actual content.
            if content.strip():
                messages.append({
                    "role": role,
                    "content": content
                })

    return messages
