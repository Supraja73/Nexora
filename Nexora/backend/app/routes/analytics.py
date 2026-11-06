from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.services.analytics_service import analytics_service

router = APIRouter(prefix="/api/analytics", tags=["Analytics"])

@router.get("/overview")
def get_analytics_overview(
    timeframe: int = Query(60, ge=5, le=1440, description="Timeframe in minutes"),
    db: Session = Depends(get_db)
):
    """Retrieve system-wide aggregated metrics, timeline curves, and container distribution."""
    return analytics_service.get_analytics_overview(db=db, timeframe_minutes=timeframe)

@router.get("/container/{container_id}")
def get_container_analytics(
    container_id: str,
    minutes: int = Query(60, ge=5, le=1440, description="Timeframe in minutes"),
    db: Session = Depends(get_db)
):
    """Retrieve historical time-series metrics for an individual container."""
    return analytics_service.get_container_history(db=db, container_id=container_id, minutes=minutes)
