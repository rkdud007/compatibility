"""Shared data schemas for coordinator and enclave services."""

from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class RoomState(str, Enum):
    """Room lifecycle states."""

    CREATED = "CREATED"
    WAITING_FOR_USERS = "WAITING_FOR_USERS"
    BOTH_UPLOADED = "BOTH_UPLOADED"
    EVALUATING = "EVALUATING"
    COMPLETED = "COMPLETED"


class UserId(str, Enum):
    """User identifiers within a room."""

    USER_A = "a"
    USER_B = "b"


class UserData(BaseModel):
    """User's public state within a room (coordinator-visible).

    Note: Actual confidential data (conversations, prompt, expected) is stored
    only in the enclave's secure storage, never in Redis.
    """

    username: Optional[str] = None
    uploaded: bool = False
    ready: bool = False


class EvaluationResult(BaseModel):
    """Compatibility evaluation scores."""

    a_to_b_score: int = Field(..., ge=0, le=100, description="How well B matches A's expectations")
    b_to_a_score: int = Field(..., ge=0, le=100, description="How well A matches B's expectations")


class RoomData(BaseModel):
    """Complete room state stored in Redis."""

    room_id: str
    state: RoomState
    created_at: float
    user_a: UserData = Field(default_factory=UserData)
    user_b: UserData = Field(default_factory=UserData)
    result: Optional[EvaluationResult] = None


# API Request/Response Models

class CreateRoomResponse(BaseModel):
    """Response for room creation."""

    room_id: str
    invite_link: str


class UploadRequest(BaseModel):
    """Request to upload user data."""

    username: str
    password: str
    conversations: list
    prompt: str
    expected: str


class UploadResponse(BaseModel):
    """Response for upload operation."""

    success: bool
    message: Optional[str] = None


class ReadyRequest(BaseModel):
    """Request to mark user as ready."""

    username: str
    password: str


class ReadyResponse(BaseModel):
    """Response for ready operation."""

    success: bool
    message: Optional[str] = None


class StatusResponse(BaseModel):
    """Response for room status polling."""

    state: RoomState
    user_a_ready: bool
    user_b_ready: bool
    user_a_username: Optional[str] = None
    user_b_username: Optional[str] = None
    result: Optional[EvaluationResult] = None


class SecureUploadRequest(BaseModel):
    """Direct upload to enclave's secure storage."""

    conversations: list
    prompt: str
    expected: str


class EvaluateRequest(BaseModel):
    """Request to enclave service for evaluation (room_id only).

    The enclave retrieves user data from its own secure storage.
    """

    room_id: str


class EvaluateResponse(BaseModel):
    """Response from enclave evaluation."""

    a_to_b_score: int = Field(..., ge=0, le=100)
    b_to_a_score: int = Field(..., ge=0, le=100)
