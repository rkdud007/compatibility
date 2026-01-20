"""Secure in-memory storage for confidential user data.

This module provides isolated storage for sensitive user data within the enclave.
Data is kept in memory only and never persisted to disk or external storage.
"""

import logging
from typing import Optional, Dict, Tuple
from threading import Lock

logger = logging.getLogger(__name__)


class SecureUserData:
    """Container for a user's confidential data."""

    def __init__(self, conversations: list, prompt: str, expected: str):
        """Initialize user data.

        Args:
            conversations: User's conversation history.
            prompt: User's confidential question.
            expected: User's expected answer.
        """
        self.conversations = conversations
        self.prompt = prompt
        self.expected = expected


class SecureStorage:
    """Thread-safe in-memory storage for confidential user data.

    This storage is enclave-only and maintains data isolation.
    Data is automatically cleaned up after evaluation completes.
    """

    def __init__(self):
        """Initialize secure storage with thread safety."""
        self._storage: Dict[Tuple[str, str], SecureUserData] = {}
        self._lock = Lock()

    def store(
        self,
        room_id: str,
        user_id: str,
        conversations: list,
        prompt: str,
        expected: str,
    ) -> None:
        """Store user's confidential data.

        Args:
            room_id: Room identifier.
            user_id: User identifier (a or b).
            conversations: User's conversation history.
            prompt: User's confidential question.
            expected: User's expected answer.
        """
        key = (room_id, user_id)
        with self._lock:
            self._storage[key] = SecureUserData(
                conversations=conversations,
                prompt=prompt,
                expected=expected,
            )
            logger.info(f"Stored confidential data for room={room_id}, user={user_id}")

    def get(self, room_id: str, user_id: str) -> Optional[SecureUserData]:
        """Retrieve user's confidential data.

        Args:
            room_id: Room identifier.
            user_id: User identifier (a or b).

        Returns:
            User's data if exists, None otherwise.
        """
        key = (room_id, user_id)
        with self._lock:
            return self._storage.get(key)

    def delete_room(self, room_id: str) -> None:
        """Delete all data for a room (both users).

        Args:
            room_id: Room identifier.
        """
        with self._lock:
            keys_to_delete = [key for key in self._storage if key[0] == room_id]
            for key in keys_to_delete:
                del self._storage[key]
            logger.info(f"Deleted all confidential data for room={room_id} ({len(keys_to_delete)} users)")

    def has_both_users(self, room_id: str) -> bool:
        """Check if both users have uploaded data.

        Args:
            room_id: Room identifier.

        Returns:
            True if both user_a and user_b data exists.
        """
        with self._lock:
            has_a = (room_id, "a") in self._storage
            has_b = (room_id, "b") in self._storage
            return has_a and has_b
