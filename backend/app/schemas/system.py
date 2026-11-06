from typing import List, Dict, Any, Optional
from pydantic import BaseModel

class DockerStatusResponse(BaseModel):
    is_connected: bool
    status: str
    message: str
    engine_version: Optional[str] = None
    api_version: Optional[str] = None
    os_type: Optional[str] = None
    architecture: Optional[str] = None
    kernel_version: Optional[str] = None
    cgroup_version: Optional[str] = None
    driver: Optional[str] = None
    endpoint: Optional[str] = None
    mode: str # 'live' or 'demo_fallback'

class SystemInfoResponse(BaseModel):
    platform: str
    release: str
    machine: str
    processor: str
    cpu_count: int
    memory_total_mb: float
    memory_available_mb: float
    memory_percent: float
    docker_status: DockerStatusResponse
    allowed_images: List[str]
    cgroup_info: Dict[str, Any]
    namespaces_info: Dict[str, Any]
