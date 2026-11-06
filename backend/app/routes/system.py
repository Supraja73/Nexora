import platform
import psutil
from fastapi import APIRouter
from app.config import settings
from app.services.docker_service import docker_service
from app.services.process_service import process_service

router = APIRouter(tags=["System & Docker"])

@router.get("/api/docker/status")
def get_docker_status():
    """Returns detailed Docker Engine connection status, driver, and API version."""
    return docker_service.get_status()

@router.get("/api/system/info")
def get_system_info():
    """Returns host operating system, CPU, memory, Docker status, and namespace architecture."""
    mem = psutil.virtual_memory()
    docker_status = docker_service.get_status()
    namespace_meta = process_service.get_namespace_architecture()
    
    return {
        "platform": platform.system(),
        "release": platform.release(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "cpu_count": psutil.cpu_count(logical=True),
        "cpu_percent": psutil.cpu_percent(interval=None),
        "memory_total_mb": round(mem.total / (1024 * 1024), 2),
        "memory_available_mb": round(mem.available / (1024 * 1024), 2),
        "memory_percent": mem.percent,
        "docker_status": docker_status,
        "allowed_images": settings.ALLOWED_IMAGES,
        "cgroup_info": {
            "version": docker_status.get("cgroup_version", "v2"),
            "subsystems": ["cpu", "memory", "pids", "io", "cpuset", "net_cls"],
            "mount_point": "/sys/fs/cgroup"
        },
        "namespaces_info": namespace_meta
    }
