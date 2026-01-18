"""Room management API routes."""

import httpx
from fastapi import APIRouter, HTTPException, BackgroundTasks
from shared.schemas import (
    CreateRoomResponse,
    UploadRequest,
    UploadResponse,
    ReadyRequest,
    ReadyResponse,
    StatusResponse,
    EvaluateRequest,
    EvaluateResponse,
    RoomState,
)

from coordinator_service.config import settings
from coordinator_service.redis_client import RedisClient

router = APIRouter(prefix="/room", tags=["rooms"])
redis_client = RedisClient()


@router.post("/create", response_model=CreateRoomResponse)
async def create_room() -> CreateRoomResponse:
    """Create a new compatibility evaluation room.

    Returns:
        Room ID and shareable invite link.
    """
    room_id = redis_client.create_room()

    # In production, this would be the actual frontend URL.
    invite_link = f"http://localhost:3000/room/{room_id}"

    return CreateRoomResponse(room_id=room_id, invite_link=invite_link)


@router.post("/{room_id}/upload", response_model=UploadResponse)
async def upload_data(room_id: str, request: UploadRequest) -> UploadResponse:
    """Upload user data to room.

    Args:
        room_id: Room identifier.
        request: Upload request with raw data.

    Returns:
        Success status.

    Raises:
        HTTPException: If room not found.
    """
    success = redis_client.upload_user_data(
        room_id=room_id,
        user_id=request.user_id,
        conversations=request.conversations,
        prompt=request.prompt,
        expected=request.expected,
    )

    if not success:
        raise HTTPException(status_code=404, detail="Room not found")

    return UploadResponse(success=True, message="Data uploaded successfully")


async def trigger_evaluation(room_id: str) -> None:
    """Trigger enclave evaluation (background task).

    Args:
        room_id: Room identifier.
    """
    room = redis_client.get_room(room_id)
    if not room or not (room.user_a.ready and room.user_b.ready):
        return

    # Set state to EVALUATING.
    redis_client.set_evaluating(room_id)

    try:
        # Call enclave service.
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{settings.enclave_service_url}/evaluate",
                json=EvaluateRequest(
                    user_a_conversations=room.user_a.conversations,
                    user_a_prompt=room.user_a.prompt,
                    user_a_expected=room.user_a.expected,
                    user_b_conversations=room.user_b.conversations,
                    user_b_prompt=room.user_b.prompt,
                    user_b_expected=room.user_b.expected,
                ).model_dump(),
            )
            response.raise_for_status()
            result = EvaluateResponse.model_validate(response.json())

        # Save result.
        from shared.schemas import EvaluationResult

        redis_client.save_result(
            room_id,
            EvaluationResult(
                a_to_b_score=result.a_to_b_score,
                b_to_a_score=result.b_to_a_score,
            ),
        )
    except Exception as e:
        # Log error and revert state (in production, would have proper error handling).
        print(f"Evaluation failed for room {room_id}: {e}")
        room = redis_client.get_room(room_id)
        if room:
            room.state = RoomState.BOTH_UPLOADED
            redis_client.update_room(room)


@router.post("/{room_id}/ready", response_model=ReadyResponse)
async def mark_ready(
    room_id: str, request: ReadyRequest, background_tasks: BackgroundTasks
) -> ReadyResponse:
    """Mark user as ready to evaluate.

    When both users are ready, triggers evaluation in background.

    Args:
        room_id: Room identifier.
        request: Ready request with user ID.
        background_tasks: FastAPI background tasks.

    Returns:
        Success status.

    Raises:
        HTTPException: If room not found or user hasn't uploaded data.
    """
    success = redis_client.mark_user_ready(room_id=room_id, user_id=request.user_id)

    if not success:
        raise HTTPException(status_code=400, detail="Room not found or user hasn't uploaded data")

    # Check if both users are ready and trigger evaluation.
    if redis_client.both_users_ready(room_id):
        background_tasks.add_task(trigger_evaluation, room_id)

    return ReadyResponse(success=True, message="User marked as ready")


@router.get("/{room_id}/status", response_model=StatusResponse)
async def get_status(room_id: str) -> StatusResponse:
    """Get current room status (for frontend polling).

    Args:
        room_id: Room identifier.

    Returns:
        Room state, ready flags, and result if completed.

    Raises:
        HTTPException: If room not found.
    """
    room = redis_client.get_room(room_id)

    if not room:
        raise HTTPException(status_code=404, detail="Room not found")

    return StatusResponse(
        state=room.state,
        user_a_ready=room.user_a.ready,
        user_b_ready=room.user_b.ready,
        result=room.result,
    )


@router.get("/health")
async def health_check() -> dict:
    """Health check endpoint.

    Returns:
        Health status and Redis connectivity.
    """
    redis_ok = redis_client.ping()
    return {"status": "ok" if redis_ok else "degraded", "redis": redis_ok}
