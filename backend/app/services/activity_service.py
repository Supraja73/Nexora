import json
from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from app.models.models import ActivityLog

class ActivityService:
    @staticmethod
    def record_activity(
        db: Session,
        event_type: str,
        description: str,
        container_id: Optional[str] = None,
        container_name: Optional[str] = None,
        status: str = "success",
        details: Optional[Dict[str, Any]] = None
    ) -> ActivityLog:
        """Create and persist an activity log event in the SQLite audit ledger."""
        details_str = json.dumps(details) if details else None
        log_entry = ActivityLog(
            timestamp=datetime.utcnow(),
            event_type=event_type,
            container_id=container_id,
            container_name=container_name,
            description=description,
            status=status,
            details_json=details_str
        )
        db.add(log_entry)
        db.commit()
        db.refresh(log_entry)
        return log_entry

    @staticmethod
    def list_activities(
        db: Session,
        limit: int = 50,
        event_type: Optional[str] = None,
        container_id: Optional[str] = None,
        search_query: Optional[str] = None
    ) -> List[ActivityLog]:
        """Fetch filtered and paginated activity logs."""
        query = db.query(ActivityLog)
        if event_type:
            query = query.filter(ActivityLog.event_type == event_type)
        if container_id:
            query = query.filter(ActivityLog.container_id == container_id)
        if search_query:
            pattern = f"%{search_query}%"
            query = query.filter(
                (ActivityLog.description.ilike(pattern)) |
                (ActivityLog.container_name.ilike(pattern)) |
                (ActivityLog.event_type.ilike(pattern))
            )
        return query.order_by(ActivityLog.timestamp.desc()).limit(limit).all()

activity_service = ActivityService()
