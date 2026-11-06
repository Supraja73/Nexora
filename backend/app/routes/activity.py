import json
from typing import Optional, List
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas.activity import ActivityListResponse, ActivityLogItem
from app.services.activity_service import activity_service

router = APIRouter(prefix="/api/activity", tags=["Activity Audit Log"])

@router.get("", response_model=ActivityListResponse)
def get_activities(
    limit: int = Query(50, ge=1, le=200),
    event_type: Optional[str] = Query(None, description="Filter by event type (create, start, stop, restart, delete, resource_update, error)"),
    container_id: Optional[str] = Query(None, description="Filter by container ID"),
    search: Optional[str] = Query(None, description="Search term in description or container name"),
    db: Session = Depends(get_db)
):
    """Retrieve audit log history of all container lifecycle operations and resource modifications."""
    logs = activity_service.list_activities(
        db=db,
        limit=limit,
        event_type=event_type,
        container_id=container_id,
        search_query=search
    )

    items = []
    for log in logs:
        details_obj = None
        if log.details_json:
            try:
                details_obj = json.loads(log.details_json)
            except Exception:
                details_obj = {"raw": log.details_json}

        items.append(
            ActivityLogItem(
                id=log.id,
                timestamp=log.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                event_type=log.event_type,
                container_id=log.container_id,
                container_name=log.container_name,
                description=log.description,
                status=log.status,
                details=details_obj
            )
        )

    return ActivityListResponse(total=len(items), items=items)
