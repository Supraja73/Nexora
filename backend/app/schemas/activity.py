from typing import Optional, List, Dict, Any
from pydantic import BaseModel

class ActivityLogItem(BaseModel):
    id: int
    timestamp: str
    event_type: str
    container_id: Optional[str] = None
    container_name: Optional[str] = None
    description: str
    status: str
    details: Optional[Dict[str, Any]] = None

class ActivityListResponse(BaseModel):
    total: int
    items: List[ActivityLogItem]
