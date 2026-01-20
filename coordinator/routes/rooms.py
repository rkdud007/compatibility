"""Room management API routes."""

import logging
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

from coordinator.config import settings
from coordinator.redis_client import RedisClient

logger = logging.getLogger(__name__)

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
    """Upload user data through coordinator to enclave.

    This endpoint proxies the user's confidential data directly to the enclave's
    secure storage, then marks the upload flag in Redis. The coordinator never
    stores the actual confidential data.

    Args:
        room_id: Room identifier.
        request: Upload request with raw data.

    Returns:
        Success status.

    Raises:
        HTTPException: If room not found or enclave upload fails.
    """
    # First, verify room exists.
    room = redis_client.get_room(room_id)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")

    # Forward confidential data to enclave's secure storage.
    try:
        from shared.schemas import SecureUploadRequest

        enclave_url = f"{settings.enclave_service_url}/upload/{room_id}/{request.user_id.value}"
        logger.info(f"Forwarding confidential data to enclave for room={room_id}, user={request.user_id}")

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                enclave_url,
                json=SecureUploadRequest(
                    conversations=request.conversations,
                    prompt=request.prompt,
                    expected=request.expected,
                ).model_dump(),
            )
            response.raise_for_status()
            logger.info(f"Enclave confirmed secure storage for room={room_id}, user={request.user_id}")

    except httpx.HTTPStatusError as e:
        logger.error(f"Enclave rejected upload: {e.response.status_code} - {e.response.text}")
        raise HTTPException(
            status_code=502,
            detail="Failed to store data in secure enclave",
        )
    except httpx.RequestError as e:
        logger.error(f"Failed to connect to enclave: {e}")
        raise HTTPException(
            status_code=503,
            detail="Enclave service unavailable",
        )

    # Mark user as uploaded in Redis (flag only, no data).
    success = redis_client.mark_user_uploaded(
        room_id=room_id,
        user_id=request.user_id,
    )

    if not success:
        raise HTTPException(status_code=404, detail="Room not found")

    return UploadResponse(success=True, message="Data uploaded successfully")


async def trigger_evaluation(room_id: str) -> None:
    """Trigger enclave evaluation (background task).

    The coordinator sends only the room_id to the enclave.
    The enclave retrieves confidential data from its own secure storage.

    Args:
        room_id: Room identifier.
    """
    logger.info(f"Starting evaluation for room {room_id}")

    room = redis_client.get_room(room_id)
    if not room or not (room.user_a.ready and room.user_b.ready):
        logger.warning(f"Cannot evaluate room {room_id}: room not found or users not ready")
        return

    # Set state to EVALUATING.
    redis_client.set_evaluating(room_id)
    logger.info(f"Room {room_id} state set to EVALUATING")

    try:
        # Call enclave service with only room_id.
        enclave_url = f"{settings.enclave_service_url}/evaluate"
        logger.info(f"Calling enclave service at {enclave_url} for room {room_id}")

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                enclave_url,
                json=EvaluateRequest(
                    room_id=room_id,
                ).model_dump(),
            )

            logger.info(f"Enclave service responded with status {response.status_code} for room {room_id}")
            response.raise_for_status()
            result = EvaluateResponse.model_validate(response.json())
            logger.info(f"Evaluation completed for room {room_id}: a_to_b={result.a_to_b_score}, b_to_a={result.b_to_a_score}")

        # Save result.
        from shared.schemas import EvaluationResult

        redis_client.save_result(
            room_id,
            EvaluationResult(
                a_to_b_score=result.a_to_b_score,
                b_to_a_score=result.b_to_a_score,
            ),
        )
        logger.info(f"Results saved for room {room_id}")
    except httpx.HTTPStatusError as e:
        logger.error(f"Enclave service returned error for room {room_id}: {e.response.status_code} - {e.response.text}")
        room = redis_client.get_room(room_id)
        if room:
            room.state = RoomState.BOTH_UPLOADED
            redis_client.update_room(room)
    except httpx.RequestError as e:
        logger.error(f"Failed to connect to enclave service for room {room_id}: {e}")
        room = redis_client.get_room(room_id)
        if room:
            room.state = RoomState.BOTH_UPLOADED
            redis_client.update_room(room)
    except Exception as e:
        logger.error(f"Evaluation failed for room {room_id}: {e}", exc_info=True)
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
