from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from app.services.docker_service import docker_service
from app.services.activity_service import activity_service
from app.models.models import SystemAlert
from app.utils.security import validate_resource_bounds
from datetime import datetime

class ResourceService:
    @staticmethod
    def calculate_cgroup_parameters(cpu_limit: float, memory_limit_mb: int) -> Dict[str, Any]:
        """
        Calculate kernel cgroup v1 and v2 control attributes:
        - cpu.cfs_quota_us = cores * 100000
        - cpu.cfs_period_us = 100000
        - memory.max / memory.limit_in_bytes = memory_limit_mb * 1024 * 1024
        - nano_cpus = int(cores * 1e9)
        """
        period_us = 100000  # Default CFS period 100ms
        quota_us = int(cpu_limit * period_us)
        mem_bytes = int(memory_limit_mb * 1024 * 1024)
        nano_cpus = int(cpu_limit * 1e9)

        return {
            "cpu_limit_cores": cpu_limit,
            "cpu_period_us": period_us,
            "cpu_quota_us": quota_us,
            "nano_cpus": nano_cpus,
            "memory_limit_mb": memory_limit_mb,
            "memory_limit_bytes": mem_bytes,
            "cgroup_v2_cpu_max": f"{quota_us} {period_us}",
            "cgroup_v2_memory_max": f"{mem_bytes}"
        }

    @staticmethod
    def get_container_resource_profile(container_id: str, db: Optional[Session] = None) -> Dict[str, Any]:
        """Fetch real-time resource allocations, consumption, and evaluate utilization warnings."""
        stats = docker_service.get_container_stats(container_id)
        cgroup_params = ResourceService.calculate_cgroup_parameters(
            stats["cpu_cores_allocated"],
            int(stats["memory_limit_mb"])
        )
        
        # High utilization warning generation (>85%)
        is_mem_warning = stats["memory_percent"] >= 85.0
        is_cpu_warning = stats["cpu_percent"] >= (stats["cpu_cores_allocated"] * 85.0)

        warning_message = None
        if is_mem_warning:
            warning_message = f"High Memory Utilization Alert: Container '{stats['container_name']}' is consuming {stats['memory_percent']}% of its cgroup limit ({stats['memory_used_mb']}MB / {stats['memory_limit_mb']}MB)."
            if db:
                alert = SystemAlert(
                    timestamp=datetime.utcnow(),
                    alert_type="memory_high",
                    severity="warning",
                    message=warning_message,
                    container_id=container_id
                )
                db.add(alert)
                db.commit()

        return {
            "container_id": stats["container_id"],
            "container_name": stats["container_name"],
            "status": stats["status"],
            "cpu": {
                "cores_allocated": stats["cpu_cores_allocated"],
                "current_percent": stats["cpu_percent"],
                "quota_us": cgroup_params["cpu_quota_us"],
                "period_us": cgroup_params["cpu_period_us"],
                "cgroup_file": "/sys/fs/cgroup/cpu.max"
            },
            "memory": {
                "used_mb": stats["memory_used_mb"],
                "limit_mb": stats["memory_limit_mb"],
                "percent": stats["memory_percent"],
                "limit_bytes": cgroup_params["memory_limit_bytes"],
                "cgroup_file": "/sys/fs/cgroup/memory.max",
                "warning": is_mem_warning
            },
            "cgroup_parameters": cgroup_params,
            "warning_message": warning_message
        }

    @staticmethod
    def update_container_resources(
        container_id: str,
        cpu_limit: Optional[float] = None,
        memory_limit_mb: Optional[int] = None,
        db: Optional[Session] = None
    ) -> Dict[str, Any]:
        """Validate bounds and update cgroup limits dynamically."""
        validate_resource_bounds(cpu_limit, memory_limit_mb)
        
        result = docker_service.update_resources(
            container_id=container_id,
            cpu_limit=cpu_limit,
            memory_limit_mb=memory_limit_mb
        )

        # Log activity
        if db:
            activity_service.record_activity(
                db=db,
                event_type="resource_update",
                description=f"Updated cgroup resource limits on container: CPU={cpu_limit} cores, Memory={memory_limit_mb}MB",
                container_id=container_id,
                status="success",
                details={"cpu_limit": cpu_limit, "memory_limit_mb": memory_limit_mb}
            )

        return result

resource_service = ResourceService()
