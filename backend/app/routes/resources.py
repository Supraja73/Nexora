from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas.container import ContainerResourceUpdate
from app.services.resource_service import resource_service
from docker.errors import NotFound

router = APIRouter(prefix="/api/containers", tags=["Resource Management & cgroups"])

@router.get("/{container_id}/resources")
def get_container_resources(container_id: str, db: Session = Depends(get_db)):
    """Retrieve cgroup limits, current utilization, quotas, and utilization alerts."""
    try:
        return resource_service.get_container_resource_profile(container_id, db=db)
    except NotFound:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Container '{container_id}' not found.")
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.post("/{container_id}/resources")
def update_container_resources(container_id: str, payload: ContainerResourceUpdate, db: Session = Depends(get_db)):
    """
    Dynamically update CPU quota (nano_cpus) and Memory limit (mem_limit)
    via Linux cgroups without restarting the container.
    """
    try:
        return resource_service.update_container_resources(
            container_id=container_id,
            cpu_limit=payload.cpu_limit,
            memory_limit_mb=payload.memory_limit_mb,
            db=db
        )
    except NotFound:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Container '{container_id}' not found.")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
