from app.routes.health import router as health_router
from app.routes.system import router as system_router
from app.routes.containers import router as containers_router
from app.routes.processes import router as processes_router
from app.routes.resources import router as resources_router
from app.routes.monitoring import router as monitoring_router
from app.routes.analytics import router as analytics_router
from app.routes.activity import router as activity_router

__all__ = [
    "health_router",
    "system_router",
    "containers_router",
    "processes_router",
    "resources_router",
    "monitoring_router",
    "analytics_router",
    "activity_router"
]
