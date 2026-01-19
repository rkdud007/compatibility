"""Coordinator service FastAPI application."""

import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from coordinator_service.routes import rooms

# Configure logging.
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

app = FastAPI(
    title="Compatibility Coordinator Service",
    description="Orchestrates compatibility evaluation rooms (untrusted component)",
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

# Include room routes.
app.include_router(rooms.router)


@app.get("/")
async def root() -> dict:
    """Root endpoint.

    Returns:
        Service information.
    """
    return {
        "service": "compatibility-coordinator",
        "version": "0.1.0",
        "status": "running",
    }
