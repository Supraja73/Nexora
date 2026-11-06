import psutil
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas.monitoring import MonitoringOverview
from app.services.docker_service import docker_service
from app.services.analytics_service import analytics_service

router = APIRouter(prefix="/api/monitoring", tags=["Live Monitoring"])

@router.get("/overview", response_model=MonitoringOverview)
def get_monitoring_overview():
    """Returns aggregated real-time monitoring stats across all active containers and host."""
    containers = docker_service.list_containers(all_containers=True)
    docker_status = docker_service.get_status()
    
    running = [c for c in containers if c["status"] == "running"]
    stopped = [c for c in containers if c["status"] in ("exited", "created", "dead")]
    paused = [c for c in containers if c["status"] == "paused"]

    total_procs = 0
    total_cpu_pct = 0.0
    total_mem_used_mb = 0.0
    total_mem_limit_mb = 0.0

    for c in running:
        st = docker_service.get_container_stats(c["id"])
        total_procs += st["pids_current"]
        total_cpu_pct += st["cpu_percent"]
        total_mem_used_mb += st["memory_used_mb"]
        total_mem_limit_mb += st["memory_limit_mb"]

    overall_mem_pct = round((total_mem_used_mb / total_mem_limit_mb * 100.0), 2) if total_mem_limit_mb > 0 else 0.0
    avg_cpu = round(total_cpu_pct / len(running), 2) if running else 0.0

    mem = psutil.virtual_memory()
    
    # Calculate system uptime
    boot_time = datetime.fromtimestamp(psutil.boot_time(), tz=timezone.utc)
    uptime_sec = int((datetime.now(timezone.utc) - boot_time).total_seconds())

    return {
        "total_containers": len(containers),
        "running_containers": len(running),
        "stopped_containers": len(stopped),
        "paused_containers": len(paused),
        "total_active_processes": total_procs,
        "avg_cpu_percent": avg_cpu,
        "total_memory_used_mb": round(total_mem_used_mb, 2),
        "total_memory_limit_mb": round(total_mem_limit_mb, 2),
        "overall_memory_percent": overall_mem_pct,
        "docker_status": docker_status["status"],
        "docker_version": docker_status.get("engine_version", "26.1"),
        "host_os": docker_status.get("os_type", "linux"),
        "host_cpu_percent": psutil.cpu_percent(interval=None),
        "host_memory_percent": mem.percent,
        "host_total_ram_gb": round(mem.total / (1024 ** 3), 2),
        "uptime_seconds": uptime_sec,
        "last_updated": datetime.now(timezone.utc).isoformat()
    }

@router.get("/history")
def get_monitoring_history(
    container_id: Optional[str] = Query(None, description="Optional container ID filter"),
    minutes: int = Query(30, ge=1, le=1440, description="Time window in minutes"),
    db: Session = Depends(get_db)
):
    """Retrieve time-series metric snapshots for charts."""
    if container_id:
        return analytics_service.get_container_history(db=db, container_id=container_id, minutes=minutes)
    
    # Overview history
    return analytics_service.get_analytics_overview(db=db, timeframe_minutes=minutes)
