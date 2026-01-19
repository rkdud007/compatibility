"""Enclave service FastAPI application."""

import logging
from fastapi import FastAPI, HTTPException
from shared.schemas import EvaluateRequest, EvaluateResponse

from enclave_service.evaluator import CompatibilityEvaluator

# Configure logging.
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Compatibility Enclave Service",
    description="Stateless evaluation service (trusted component - runs in TEE)",
    version="0.1.0",
)

# Initialize evaluator.
evaluator = CompatibilityEvaluator()


@app.post("/evaluate", response_model=EvaluateResponse)
async def evaluate(request: EvaluateRequest) -> EvaluateResponse:
    """Evaluate compatibility between two users.

    This endpoint receives user data and performs evaluation using OpenAI.

    Args:
        request: User data for both users.

    Returns:
        Compatibility scores (0-100) for both directions.

    Raises:
        HTTPException: If evaluation fails.
    """
    logger.info("Received evaluation request")
    logger.debug(f"User A conversations: {len(request.user_a_conversations)} messages")
    logger.debug(f"User B conversations: {len(request.user_b_conversations)} messages")

    try:
        a_to_b_score, b_to_a_score = evaluator.evaluate(
            user_a_conversations=request.user_a_conversations,
            user_a_prompt=request.user_a_prompt,
            user_a_expected=request.user_a_expected,
            user_b_conversations=request.user_b_conversations,
            user_b_prompt=request.user_b_prompt,
            user_b_expected=request.user_b_expected,
        )

        logger.info(f"Evaluation completed: a_to_b={a_to_b_score}, b_to_a={b_to_a_score}")

        return EvaluateResponse(
            a_to_b_score=a_to_b_score,
            b_to_a_score=b_to_a_score,
        )

    except Exception as e:
        logger.error(f"Evaluation failed: {e}", exc_info=True)
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
