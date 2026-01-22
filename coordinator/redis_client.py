"""Redis client for room state management."""

import json
import time
from typing import Optional
from uuid import uuid4

import redis
from shared.schemas import RoomData, RoomState, UserData, UserId, EvaluationResult

from coordinator.config import settings


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

    def get_or_assign_user_id(self, room_id: str, username: str) -> Optional[UserId]:
        """Get existing user_id for username, or assign user_a/user_b slot.

        Args:
            room_id: Room identifier.
            username: User's username.

        Returns:
            UserId (USER_A or USER_B) if successful, None if room full.
        """
        room = self.get_room(room_id)
        if not room:
            return None

        # Check if user already has a slot.
        if room.user_a.username == username:
            return UserId.USER_A
        if room.user_b.username == username:
            return UserId.USER_B

        # Assign new slot.
        if room.user_a.username is None:
            return UserId.USER_A
        elif room.user_b.username is None:
            return UserId.USER_B
        else:
            # Room is full.
            return None

    def mark_user_uploaded(
        self,
        room_id: str,
        username: str,
        password: str,
    ) -> Optional[UserId]:
        """Mark user as having uploaded data (flag only, no actual data stored).

        The actual confidential data is stored directly in the enclave's
        secure storage, never in Redis.

        Args:
            room_id: Room identifier.
            username: User's username.
            password: User's password (stored for client-side validation).

        Returns:
            UserId if successful, None if room not found or full.
        """
        room = self.get_room(room_id)
        if not room:
            return None

        # Get or assign user_id.
        user_id = self.get_or_assign_user_id(room_id, username)
        if not user_id:
            return None

        # Update user data with username and uploaded flag.
        user_data = UserData(
            username=username,
            uploaded=True,
            ready=False,
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
        return user_id

    def mark_user_ready(self, room_id: str, username: str) -> bool:
        """Mark user as ready.

        Args:
            room_id: Room identifier.
            username: User's username.

        Returns:
            True if successful, False if room not found or user hasn't uploaded.
        """
        room = self.get_room(room_id)
        if not room:
            return False

        # Find user by username.
        user_id = None
        if room.user_a.username == username:
            user_id = UserId.USER_A
        elif room.user_b.username == username:
            user_id = UserId.USER_B
        else:
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
