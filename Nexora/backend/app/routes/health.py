from fastapi import APIRouter
from datetime import datetime, timezone
from app.config import settings
from app.services.docker_service import docker_service

router = APIRouter(tags=["Health"])

@router.get("/api/health")
def get_health():
    """Health check endpoint returning application status, version and Docker connectivity."""
    docker_status = docker_service.get_status()
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "title": settings.APP_TITLE,
        "version": settings.APP_VERSION,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "docker": {
            "mode": docker_status["mode"],
            "status": docker_status["status"],
            "connected": docker_status["is_connected"]
        }
    }
