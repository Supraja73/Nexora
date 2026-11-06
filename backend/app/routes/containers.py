from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas.container import (
    ContainerCreateRequest,
    ContainerSummary,
    ContainerDetail
)
from app.schemas.monitoring import LiveStatsResponse
from app.services.docker_service import docker_service
from app.services.activity_service import activity_service
from app.utils.security import sanitize_container_name, validate_image_name, validate_port_mapping_security
from docker.errors import NotFound, APIError

router = APIRouter(prefix="/api/containers", tags=["Containers"])

@router.get("", response_model=List[ContainerSummary])
def list_containers(all: bool = Query(True, description="Include stopped/exited containers")):
    """List all Linux containers with real-time cgroup status and resource usage."""
    return docker_service.list_containers(all_containers=all)

@router.post("", status_code=status.HTTP_201_CREATED)
def create_container(payload: ContainerCreateRequest, db: Session = Depends(get_db)):
    """Create and start a new isolated Linux container with cgroup constraints."""
    clean_name = sanitize_container_name(payload.name)
    clean_image = validate_image_name(payload.image)
    validate_port_mapping_security(payload.port_mapping)

    try:
        result = docker_service.create_container(
            name=clean_name,
            image=clean_image,
            cpu_limit=payload.cpu_limit,
            memory_limit_mb=payload.memory_limit_mb,
            port_mapping=payload.port_mapping,
            restart_policy=payload.restart_policy,
            command=payload.command
        )

        activity_service.record_activity(
            db=db,
            event_type="create",
            description=f"Created container '{clean_name}' using image {clean_image} (CPU: {payload.cpu_limit} cores, RAM: {payload.memory_limit_mb}MB)",
            container_id=result["id"],
            container_name=clean_name,
            status="success",
            details=payload.model_dump()
        )
        return result
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as e:
        activity_service.record_activity(
            db=db,
            event_type="error",
            description=f"Failed to create container '{clean_name}': {str(e)}",
            container_name=clean_name,
            status="failure"
        )
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Container creation failed: {str(e)}")

@router.get("/{container_id}", response_model=ContainerDetail)
def inspect_container(container_id: str):
    """Retrieve deep container configuration, cgroups path, and namespace details."""
    try:
        return docker_service.inspect_container(container_id)
    except NotFound:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Container '{container_id}' not found.")
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.post("/{container_id}/start")
def start_container(container_id: str, db: Session = Depends(get_db)):
    """Start an existing container."""
    try:
        res = docker_service.start_container(container_id)
        activity_service.record_activity(
            db=db,
            event_type="start",
            description=f"Started container {container_id[:12]}",
            container_id=container_id,
            status="success"
        )
        return res
    except NotFound:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Container '{container_id}' not found.")
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.post("/{container_id}/stop")
def stop_container(container_id: str, timeout: int = 10, db: Session = Depends(get_db)):
    """Gracefully stop a running container."""
    try:
        res = docker_service.stop_container(container_id, timeout=timeout)
        activity_service.record_activity(
            db=db,
            event_type="stop",
            description=f"Stopped container {container_id[:12]}",
            container_id=container_id,
            status="success"
        )
        return res
    except NotFound:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Container '{container_id}' not found.")
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.post("/{container_id}/restart")
def restart_container(container_id: str, timeout: int = 10, db: Session = Depends(get_db)):
    """Restart a container."""
    try:
        res = docker_service.restart_container(container_id, timeout=timeout)
        activity_service.record_activity(
            db=db,
            event_type="restart",
            description=f"Restarted container {container_id[:12]}",
            container_id=container_id,
            status="success"
        )
        return res
    except NotFound:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Container '{container_id}' not found.")
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.post("/{container_id}/pause")
def pause_container(container_id: str, db: Session = Depends(get_db)):
    """Pause all processes within the container using the cgroup freezer."""
    try:
        res = docker_service.pause_container(container_id)
        activity_service.record_activity(
            db=db,
            event_type="pause",
            description=f"Paused container processes for {container_id[:12]}",
            container_id=container_id,
            status="success"
        )
        return res
    except NotFound:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Container '{container_id}' not found.")
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.post("/{container_id}/unpause")
def unpause_container(container_id: str, db: Session = Depends(get_db)):
    """Resume execution of all processes within the container."""
    try:
        res = docker_service.unpause_container(container_id)
        activity_service.record_activity(
            db=db,
            event_type="unpause",
            description=f"Resumed container processes for {container_id[:12]}",
            container_id=container_id,
            status="success"
        )
        return res
    except NotFound:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Container '{container_id}' not found.")
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.delete("/{container_id}")
def remove_container(container_id: str, force: bool = False, db: Session = Depends(get_db)):
    """Remove a container from the system."""
    try:
        res = docker_service.remove_container(container_id, force=force)
        activity_service.record_activity(
            db=db,
            event_type="delete",
            description=f"Removed container {container_id[:12]} (force={force})",
            container_id=container_id,
            status="success"
        )
        return res
    except NotFound:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Container '{container_id}' not found.")
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.get("/{container_id}/stats", response_model=LiveStatsResponse)
def get_container_stats(container_id: str):
    """Retrieve real-time metrics for CPU, RAM, Network I/O, and PIDs."""
    try:
        return docker_service.get_container_stats(container_id)
    except NotFound:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Container '{container_id}' not found.")
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
