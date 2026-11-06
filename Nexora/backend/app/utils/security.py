import re
from typing import Optional
from fastapi import HTTPException
from app.config import settings

CONTAINER_NAME_REGEX = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_.-]{1,63}$")
IMAGE_NAME_REGEX = re.compile(r"^[a-z0-9]+(?:[._-][a-z0-9]+)*(?:/[a-z0-9]+(?:[._-][a-z0-9]+)*)*(?::[a-zA-Z0-9_.-]+)?$")

def sanitize_container_name(name: str) -> str:
    """Validate and sanitize container name against injection or path traversal."""
    cleaned = name.strip()
    if not CONTAINER_NAME_REGEX.match(cleaned):
        raise HTTPException(
            status_code=400,
            detail="Invalid container name. Must be 2-64 characters and contain only alphanumeric, '_', '-', or '.' characters."
        )
    return cleaned

def validate_image_name(image: str) -> str:
    """Ensure image is in allowed whitelist or conforms to safe Docker image specification."""
    cleaned = image.strip()
    if not IMAGE_NAME_REGEX.match(cleaned):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid image format: '{cleaned}'. Must be a valid Docker image reference."
        )
    
    # Check if exact match in allowed images or base match
    is_allowed = False
    for allowed in settings.ALLOWED_IMAGES:
        if cleaned == allowed or cleaned.startswith(f"{allowed.split(':')[0]}:"):
            is_allowed = True
            break
            
    if not is_allowed and cleaned not in settings.ALLOWED_IMAGES:
        # If user typed something not explicitly in list, let's verify it has no dangerous params
        allowed_prefixes = ("alpine", "nginx", "python", "redis", "busybox", "ubuntu", "node", "memcached", "httpd", "traefik")
        if not any(cleaned.startswith(p) for p in allowed_prefixes):
            raise HTTPException(
                status_code=400,
                detail=f"Image '{cleaned}' is not permitted by NEXORA security policy. Allowed images: {', '.join(settings.ALLOWED_IMAGES)}"
            )
    return cleaned

def validate_resource_bounds(cpu_limit: Optional[float], memory_limit_mb: Optional[int]):
    """Ensure requested resource allocations are within safe host boundaries."""
    if cpu_limit is not None:
        if cpu_limit < settings.MIN_CONTAINER_CPUS or cpu_limit > settings.MAX_CONTAINER_CPUS:
            raise HTTPException(
                status_code=400,
                detail=f"CPU limit must be between {settings.MIN_CONTAINER_CPUS} and {settings.MAX_CONTAINER_CPUS} cores."
            )
    if memory_limit_mb is not None:
        if memory_limit_mb < settings.MIN_CONTAINER_MEMORY_MB or memory_limit_mb > settings.MAX_CONTAINER_MEMORY_MB:
            raise HTTPException(
                status_code=400,
                detail=f"Memory limit must be between {settings.MIN_CONTAINER_MEMORY_MB}MB and {settings.MAX_CONTAINER_MEMORY_MB}MB."
            )

def validate_port_mapping_security(port_mapping: Optional[str]) -> Optional[dict]:
    """Validate port map and prohibit reserved sensitive ports (e.g. 22 SSH, 3389 RDP)."""
    if not port_mapping:
        return None
    try:
        host_port_str, container_port_str = port_mapping.split(":")
        host_port = int(host_port_str)
        container_port = int(container_port_str)
    except Exception:
        raise HTTPException(status_code=400, detail="Port mapping must be in HOST:CONTAINER format (e.g. '8080:80')")
    
    restricted_ports = {22, 23, 25, 445, 3389, 2375, 2376}
    if host_port in restricted_ports:
        raise HTTPException(
            status_code=400,
            detail=f"Host port {host_port} is reserved for sensitive host services and cannot be mapped."
        )
    if not (1 <= host_port <= 65535 and 1 <= container_port <= 65535):
        raise HTTPException(status_code=400, detail="Ports must be in valid TCP/UDP range (1-65535).")
        
    return {f"{container_port}/tcp": host_port}
