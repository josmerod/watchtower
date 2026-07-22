"""Main API entry point."""

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.routers import router

app = FastAPI(
    title="Watchtower API",
    description="API for accessing Watchtower news and knowledge data.",
    version="0.1.0",
)

# Configure CORS. ADDITIONAL_CORS_ORIGINS (comma-separated) lets the deployed
# environment allow the LAN/dashboard origin without hardcoding an IP here.
_extra = [o.strip() for o in os.getenv("ADDITIONAL_CORS_ORIGINS", "").split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:45714",
        "http://127.0.0.1:45714",
        "https://watchtower.josmerod.es",
        *_extra,
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api/v1")


# Health check at both root and API prefix for convenience
@app.get("/health")
@app.get("/api/v1/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok"}
