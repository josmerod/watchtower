"""Main API entry point."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.routers import router
from src.config.settings import get_settings

app = FastAPI(
    title="Watchtower API",
    description="API for accessing Watchtower news and knowledge data.",
    version="0.1.0",
)

# Configure CORS — read-only API, restrict origins from config and methods to GET
settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.api.cors_origins,
    allow_credentials=True,
    allow_methods=settings.api.cors_methods,
    allow_headers=["Authorization", "Content-Type"],
)

app.include_router(router, prefix="/api/v1")


# Health check at both root and API prefix for convenience
@app.get("/health")
@app.get("/api/v1/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok"}
