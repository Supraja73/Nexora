from typing import List, Dict, Any
from fastapi import APIRouter, HTTPException, Body, status
from app.services.process_service import process_service
from docker.errors import NotFound

router = APIRouter(tags=["Process Isolation & Namespaces"])

@router.get("/api/containers/{container_id}/processes")
def get_container_processes(container_id: str):
    """
    Demonstrate Linux PID namespace isolation for a specific container.
    Lists container processes, mapping container PIDs to host kernel PIDs.
    """
    try:
        return process_service.get_container_processes(container_id)
    except NotFound:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Container '{container_id}' not found.")
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.get("/api/processes/architecture")
def get_namespace_architecture():
    """
    Returns educational documentation detailing the 7 Linux namespaces and
    comparing kernel process isolation vs Hypervisor virtual machines.
    """
    return process_service.get_namespace_architecture()

@router.post("/api/processes/compare")
def compare_container_processes(payload: Dict[str, List[str]] = Body(...)):
    """
    Compare processes and PID namespaces between multiple containers.
    Illustrates independent PID 1 trees running on a single host kernel.
    """
    container_ids = payload.get("container_ids", [])
    if not container_ids:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Please provide a list of container_ids to compare.")
    return process_service.compare_containers_processes(container_ids)
