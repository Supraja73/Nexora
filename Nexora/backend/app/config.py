import os
from typing import List
from pydantic import ConfigDict
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    model_config = ConfigDict(env_file=".env", extra="ignore")

    APP_NAME: str = "NEXORA"
    APP_TITLE: str = "Linux Container-Based Process Isolation and Resource Management"
    APP_TAGLINE: str = "Isolate. Monitor. Optimize."
    APP_VERSION: str = "1.0.0"
    
    # Server settings
    HOST: str = "127.0.0.1"
    PORT: int = 8000
    DEBUG: bool = True
    
    # Database
    DATABASE_URL: str = "sqlite:///./nexora.db"
    
    # Docker
    DOCKER_HOST: str | None = None
    DOCKER_TIMEOUT: int = 15
    ENABLE_DEMO_FALLBACK: bool = True
    
    # Resource management defaults & safety bounds
    MAX_CONTAINER_MEMORY_MB: int = 4096
    MIN_CONTAINER_MEMORY_MB: int = 32
    MAX_CONTAINER_CPUS: float = 4.0
    MIN_CONTAINER_CPUS: float = 0.1
    
    # Security Whitelist of Allowed Docker Images
    ALLOWED_IMAGES: List[str] = [
        "alpine:latest",
        "alpine:3.19",
        "nginx:alpine",
        "python:3.12-alpine",
        "redis:alpine",
        "busybox:latest",
        "ubuntu:latest",
        "node:20-alpine",
        "memcached:alpine"
    ]
    
    # Monitoring
    MONITORING_INTERVAL_SECONDS: int = 2
    METRICS_HISTORY_RETENTION_HOURS: int = 24
settings = Settings()
