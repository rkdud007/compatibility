"""Redis client for room state management."""

import json
import time
from typing import Optional
from uuid import uuid4

import redis
from shared.schemas import RoomData, RoomState, UserData, UserId, EvaluationResult

from coordinator_service.config import settings


class RedisClient:
    """Redis client for managing room state."""

    def __init__(self):
        """Initialize Redis connection."""
        self.redis = redis.Redis(
            host=settings.redis_host,
            port=settings.redis_port,
            db=settings.redis_db,
            decode_responses=True,
        )

    def _room_key(self, room_id: str) -> str:
        """Generate Redis key for room.

        Args:
            room_id: Room identifier.

        Returns:
            Redis key string.
        """
        return f"room:{room_id}"

    def create_room(self) -> str:
        """Create a new room with unique ID.

        Returns:
            Room ID (UUID).
        """
        room_id = str(uuid4())
        room = RoomData(
            room_id=room_id,
            state=RoomState.CREATED,
            created_at=time.time(),
        )

        key = self._room_key(room_id)
        self.redis.setex(
            name=key,
            time=settings.room_ttl_seconds,
            value=room.model_dump_json(),
        )

        return room_id

    def get_room(self, room_id: str) -> Optional[RoomData]:
        """Retrieve room data.

        Args:
            room_id: Room identifier.

        Returns:
            RoomData if exists, None otherwise.
        """
        key = self._room_key(room_id)
        data = self.redis.get(key)

        if not data:
            return None

        return RoomData.model_validate_json(data)

    def update_room(self, room: RoomData) -> None:
        """Update room data in Redis.

        Args:
            room: Updated room data.
        """
        key = self._room_key(room.room_id)
        self.redis.setex(
            name=key,
            time=settings.room_ttl_seconds,
            value=room.model_dump_json(),
        )

    def upload_user_data(
        self,
        room_id: str,
        user_id: UserId,
        conversations: list,
        prompt: str,
        expected: str,
    ) -> bool:
        """Upload user data to room.

        Args:
            room_id: Room identifier.
            user_id: User identifier (a or b).
            conversations: Conversation data.
            prompt: Prompt string.
            expected: Expected answer.

        Returns:
            True if successful, False if room not found.
        """
        room = self.get_room(room_id)
        if not room:
            return False

        # Update user data.
        user_data = UserData(
            uploaded=True,
            ready=False,
            conversations=conversations,
            prompt=prompt,
            expected=expected,
        )

        if user_id == UserId.USER_A:
            room.user_a = user_data
        else:
            room.user_b = user_data

        # Update state.
        if room.user_a.uploaded and room.user_b.uploaded:
            room.state = RoomState.BOTH_UPLOADED
        elif room.state == RoomState.CREATED:
            room.state = RoomState.WAITING_FOR_USERS

        self.update_room(room)
        return True

    def mark_user_ready(self, room_id: str, user_id: UserId) -> bool:
        """Mark user as ready.

        Args:
            room_id: Room identifier.
            user_id: User identifier (a or b).

        Returns:
            True if successful, False if room not found or user hasn't uploaded.
        """
        room = self.get_room(room_id)
        if not room:
            return False

        # Check if user has uploaded data.
        user_data = room.user_a if user_id == UserId.USER_A else room.user_b
        if not user_data.uploaded:
            return False

        # Mark ready.
        user_data.ready = True

        if user_id == UserId.USER_A:
            room.user_a = user_data
        else:
            room.user_b = user_data

        self.update_room(room)
        return True

    def both_users_ready(self, room_id: str) -> bool:
        """Check if both users are ready.

        Args:
            room_id: Room identifier.

        Returns:
            True if both users ready, False otherwise.
        """
        room = self.get_room(room_id)
        if not room:
            return False

        return room.user_a.ready and room.user_b.ready

    def set_evaluating(self, room_id: str) -> bool:
        """Set room state to EVALUATING.

        Args:
            room_id: Room identifier.

        Returns:
            True if successful, False if room not found.
        """
        room = self.get_room(room_id)
        if not room:
            return False

        room.state = RoomState.EVALUATING
        self.update_room(room)
        return True

    def save_result(self, room_id: str, result: EvaluationResult) -> bool:
        """Save evaluation result and mark room as completed.

        Args:
            room_id: Room identifier.
            result: Evaluation scores.

        Returns:
            True if successful, False if room not found.
        """
        room = self.get_room(room_id)
        if not room:
            return False

        room.result = result
        room.state = RoomState.COMPLETED
        self.update_room(room)
        return True

    def delete_room(self, room_id: str) -> None:
        """Delete room from Redis.

        Args:
            room_id: Room identifier.
        """
        key = self._room_key(room_id)
        self.redis.delete(key)

    def ping(self) -> bool:
        """Check Redis connection.

        Returns:
            True if connected, False otherwise.
        """
        try:
            return self.redis.ping()
        except Exception:
            return False
