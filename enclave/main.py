"""Enclave service FastAPI application."""

import logging
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from shared.schemas import (
    EvaluateRequest,
    EvaluateResponse,
    SecureUploadRequest,
    UserId,
)

from enclave.evaluator import CompatibilityEvaluator
from enclave.secure_storage import SecureStorage

# Configure logging.
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Compatibility Enclave Service",
    description="Secure evaluation service (trusted component - runs in TEE)",
    version="0.1.0",
)

# CORS middleware for frontend access.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict to frontend domain.
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize evaluator and secure storage.
evaluator = CompatibilityEvaluator()
secure_storage = SecureStorage()


@app.post("/upload/{room_id}/{user_id}")
async def upload_secure_data(
    room_id: str, user_id: UserId, request: SecureUploadRequest
) -> dict:
    """Store user's confidential data in secure enclave storage.

    This endpoint receives sensitive user data and stores it in memory
    within the enclave. Data never leaves the enclave or touches Redis.

    Args:
        room_id: Room identifier.
        user_id: User identifier (a or b).
        request: User's confidential data.

    Returns:
        Success confirmation (no data echoed back).
    """
    logger.info(f"Received secure upload for room={room_id}, user={user_id}")
    logger.debug(f"Conversations: {len(request.conversations)} messages")

    secure_storage.store(
        room_id=room_id,
        user_id=user_id.value,
        conversations=request.conversations,
        prompt=request.prompt,
        expected=request.expected,
    )

    return {
        "success": True,
        "message": "Data securely stored in enclave",
    }


@app.post("/evaluate", response_model=EvaluateResponse)
async def evaluate(request: EvaluateRequest) -> EvaluateResponse:
    """Evaluate compatibility between two users.

    This endpoint retrieves confidential data from secure storage,
    performs evaluation, and cleans up the data afterward.

    Args:
        request: Evaluation request with room_id only.

    Returns:
        Compatibility scores (0-100) for both directions.

    Raises:
        HTTPException: If data not found or evaluation fails.
    """
    room_id = request.room_id
    logger.info(f"Received evaluation request for room={room_id}")

    # Retrieve confidential data from secure storage.
    user_a_data = secure_storage.get(room_id, "a")
    user_b_data = secure_storage.get(room_id, "b")

    if not user_a_data or not user_b_data:
        logger.error(f"Missing user data for room={room_id}")
        raise HTTPException(
            status_code=400,
            detail="Both users must upload data before evaluation",
        )

    logger.debug(f"User A conversations: {len(user_a_data.conversations)} messages")
    logger.debug(f"User B conversations: {len(user_b_data.conversations)} messages")

    try:
        a_to_b_score, b_to_a_score = evaluator.evaluate(
            user_a_conversations=user_a_data.conversations,
            user_a_prompt=user_a_data.prompt,
            user_a_expected=user_a_data.expected,
            user_b_conversations=user_b_data.conversations,
            user_b_prompt=user_b_data.prompt,
            user_b_expected=user_b_data.expected,
        )

        logger.info(f"Evaluation completed: a_to_b={a_to_b_score}, b_to_a={b_to_a_score}")

        # Clean up confidential data after evaluation.
        secure_storage.delete_room(room_id)
        logger.info(f"Cleaned up confidential data for room={room_id}")

        return EvaluateResponse(
            a_to_b_score=a_to_b_score,
            b_to_a_score=b_to_a_score,
        )

    except Exception as e:
        logger.error(f"Evaluation failed for room={room_id}: {e}", exc_info=True)
        # Clean up even on failure.
        secure_storage.delete_room(room_id)
        raise HTTPException(
            status_code=500,
            detail=f"Evaluation failed: {str(e)}",
        )


@app.get("/health")
async def health_check() -> dict:
    """Health check endpoint.

    Returns:
        Service status.
    """
    return {"status": "ok", "service": "enclave"}


@app.get("/")
async def root() -> dict:
    """Root endpoint.

    Returns:
        Service information.
    """
    return {
        "service": "compatibility-enclave",
        "version": "0.1.0",
        "status": "running",
        "note": "Stateless evaluation service - no data persistence",
    }
