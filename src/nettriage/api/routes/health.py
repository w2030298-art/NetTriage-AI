"""Health check route for NetTriage AI."""

from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/healthz")
async def health_check() -> dict[str, str]:
    """Health check endpoint returning application status."""
    return {"status": "ok", "app": "NetTriage AI", "version": "0.1.0"}
