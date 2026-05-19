"""Main API entry point."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.api.routers import router

app = FastAPI(
    title="Watchtower API",
    description="API for accessing Watchtower news and knowledge data.",
    version="0.1.0",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:45714",
        "http://127.0.0.1:45714",
        "http://192.168.31.126:45714",
        "https://watchtower.josmerod.es",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api/v1")

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok"}
