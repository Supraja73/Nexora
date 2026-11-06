import os
import sys
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.config import settings
from app.database import init_db, SessionLocal
from app.monitoring.collector import collector
from app.services.activity_service import activity_service
from app.models.models import ActivityLog
from app.routes import (
    health_router,
    system_router,
    containers_router,
    processes_router,
    resources_router,
    monitoring_router,
    analytics_router,
    activity_router
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize Database schema
    init_db()
    
    # Seed initial activity log if table is empty
    db = SessionLocal()
    try:
        count = db.query(ActivityLog).count()
        if count == 0:
            activity_service.record_activity(
                db=db,
                event_type="system",
                description="NEXORA Linux Container Management Platform initialized successfully.",
                status="success",
                details={"version": settings.APP_VERSION, "isolation": "cgroups_and_namespaces"}
            )
    finally:
        db.close()

    # Start metrics collector in background
    await collector.start()
    
    yield
    
    # Shutdown: Stop collector
    await collector.stop()

app = FastAPI(
    title=f"{settings.APP_NAME} - {settings.APP_TITLE}",
    description="Enterprise-grade Linux container-based process isolation, cgroups resource management, live telemetry and audit logging platform.",
    version=settings.APP_VERSION,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API Routers
app.include_router(health_router)
app.include_router(system_router)
app.include_router(containers_router)
app.include_router(processes_router)
app.include_router(resources_router)
app.include_router(monitoring_router)
app.include_router(analytics_router)
app.include_router(activity_router)

# Mount frontend files
frontend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "frontend"))
if os.path.exists(frontend_dir):
    app.mount("/static", StaticFiles(directory=frontend_dir), name="static")

    @app.get("/", include_in_schema=False)
    async def serve_index():
        index_file = os.path.join(frontend_dir, "index.html")
        if os.path.exists(index_file):
            return FileResponse(index_file)
        return {"message": "Frontend not found at expected path."}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=settings.HOST, port=settings.PORT, reload=settings.DEBUG)
