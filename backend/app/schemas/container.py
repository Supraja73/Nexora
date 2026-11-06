import re
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, field_validator

CONTAINER_NAME_REGEX = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_.-]{1,63}$")

class ContainerCreateRequest(BaseModel):
    name: str = Field(..., description="Unique container name (alphanumeric, dashes, underscores)")
    image: str = Field("alpine:latest", description="Docker image name")
    cpu_limit: float = Field(1.0, ge=0.1, le=8.0, description="CPU cores allocation (e.g. 0.5, 1.0, 2.0)")
    memory_limit_mb: int = Field(512, ge=32, le=8192, description="RAM limit in Megabytes (32MB - 8192MB)")
    port_mapping: Optional[str] = Field(None, description="Host:Container port map, e.g. '8080:80'")
    restart_policy: str = Field("no", description="Restart policy: no, always, on-failure, unless-stopped")
    command: Optional[str] = Field(None, description="Optional custom entrypoint command")

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        clean = v.strip()
        if not CONTAINER_NAME_REGEX.match(clean):
            raise ValueError("Container name must be 2-64 chars and contain only alphanumeric, '_', '-', or '.'")
        return clean

    @field_validator("port_mapping")
    @classmethod
    def validate_port_mapping(cls, v: Optional[str]) -> Optional[str]:
        if not v or not v.strip():
            return None
        parts = v.strip().split(":")
        if len(parts) != 2:
            raise ValueError("Port mapping must be in host_port:container_port format (e.g. '8080:80')")
        try:
            h_port = int(parts[0])
            c_port = int(parts[1])
            if not (1 <= h_port <= 65535 and 1 <= c_port <= 65535):
                raise ValueError("Ports must be between 1 and 65535")
        except ValueError as err:
            raise ValueError(f"Invalid port specification: {err}")
        return f"{h_port}:{c_port}"

    @field_validator("restart_policy")
    @classmethod
    def validate_restart_policy(cls, v: str) -> str:
        allowed = ["no", "always", "on-failure", "unless-stopped"]
        if v not in allowed:
            raise ValueError(f"Restart policy must be one of {allowed}")
        return v

class ContainerResourceUpdate(BaseModel):
    cpu_limit: Optional[float] = Field(None, ge=0.1, le=8.0, description="Updated CPU cores limit")
    memory_limit_mb: Optional[int] = Field(None, ge=32, le=8192, description="Updated RAM limit in MB")

class ContainerSummary(BaseModel):
    id: str
    short_id: str
    name: str
    image: str
    status: str # running, exited, paused, restarting, created
    created: str
    uptime: str
    cpu_limit: float
    memory_limit_mb: int
    cpu_percent: float
    memory_used_mb: float
    memory_percent: float
    port_mapping: Optional[str] = None
    restart_policy: str = "no"
    pids_count: int = 0
    health: str = "healthy"

class ProcessItem(BaseModel):
    container_pid: int
    host_pid: int
    user: str
    cpu_percent: float
    mem_percent: float
    vsz: str
    rss: str
    stat: str
    command: str

class ProcessIsolationInspection(BaseModel):
    container_id: str
    container_name: str
    pid_namespace_id: str
    processes: List[ProcessItem]
    total_processes: int
    kernel_version: str
    namespace_explanation: Dict[str, Any]

class ContainerDetail(BaseModel):
    id: str
    name: str
    image: str
    status: str
    created: str
    platform: str
    driver: str
    cgroups_path: Optional[str]
    cgroup_version: str
    ip_address: Optional[str]
    mac_address: Optional[str]
    ports: Dict[str, Any]
    env_vars: List[str]
    mounts: List[Dict[str, Any]]
    cpu_limit: float
    cpu_quota: Optional[int]
    cpu_period: Optional[int]
    memory_limit_mb: int
    memory_swap_limit_mb: Optional[int]
    restart_policy: str
    command: Optional[str]
