from datetime import datetime, timedelta, timezone
from typing import Dict, List, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.models import MetricSnapshot, ActivityLog
from app.services.docker_service import docker_service

class AnalyticsService:
    @staticmethod
    def get_container_history(db: Session, container_id: str, minutes: int = 60) -> List[Dict[str, Any]]:
        """Retrieve actual historical snapshots for a specific container."""
        cutoff = datetime.utcnow() - timedelta(minutes=minutes)
        rows = db.query(MetricSnapshot).filter(
            MetricSnapshot.container_id == container_id,
            MetricSnapshot.timestamp >= cutoff
        ).order_by(MetricSnapshot.timestamp.asc()).all()

        return [
            {
                "timestamp": r.timestamp.strftime("%H:%M:%S"),
                "cpu_percent": r.cpu_percent,
                "memory_used_mb": r.memory_used_mb,
                "memory_percent": r.memory_percent,
                "rx_bytes": r.rx_bytes,
                "tx_bytes": r.tx_bytes,
                "pids_count": r.pids_count
            }
            for r in rows
        ]

    @staticmethod
    def get_analytics_overview(db: Session, timeframe_minutes: int = 60) -> Dict[str, Any]:
        """Aggregate CPU, Memory, Network, and Container distribution trends."""
        cutoff = datetime.utcnow() - timedelta(minutes=timeframe_minutes)
        
        # Query snapshots
        snapshots = db.query(MetricSnapshot).filter(
            MetricSnapshot.timestamp >= cutoff
        ).order_by(MetricSnapshot.timestamp.asc()).all()

        total_points = len(snapshots)
        if total_points == 0:
            # If database is fresh, collect one snapshot right away
            containers = docker_service.list_containers(all_containers=False)
            for c in containers:
                st = docker_service.get_container_stats(c["id"])
                snap = MetricSnapshot(
                    timestamp=datetime.utcnow(),
                    container_id=c["id"],
                    container_name=c["name"],
                    cpu_percent=st["cpu_percent"],
                    memory_used_mb=st["memory_used_mb"],
                    memory_limit_mb=st["memory_limit_mb"],
                    memory_percent=st["memory_percent"],
                    rx_bytes=st["rx_bytes"],
                    tx_bytes=st["tx_bytes"],
                    block_read_bytes=st["block_read_bytes"],
                    block_write_bytes=st["block_write_bytes"],
                    pids_count=st["pids_current"]
                )
                db.add(snap)
            db.commit()
            snapshots = db.query(MetricSnapshot).filter(
                MetricSnapshot.timestamp >= cutoff
            ).order_by(MetricSnapshot.timestamp.asc()).all()
            total_points = len(snapshots)

        avg_cpu = 0.0
        peak_cpu = 0.0
        avg_mem = 0.0
        peak_mem = 0.0
        
        if total_points > 0:
            cpu_vals = [s.cpu_percent for s in snapshots]
            mem_vals = [s.memory_used_mb for s in snapshots]
            avg_cpu = round(sum(cpu_vals) / len(cpu_vals), 2)
            peak_cpu = round(max(cpu_vals), 2)
            avg_mem = round(sum(mem_vals) / len(mem_vals), 2)
            peak_mem = round(max(mem_vals), 2)

        # Timeline grouped by timestamp
        timeline_map = {}
        for s in snapshots:
            ts_key = s.timestamp.strftime("%H:%M:%S")
            if ts_key not in timeline_map:
                timeline_map[ts_key] = {"timestamp": ts_key, "cpu_total": 0.0, "mem_total": 0.0, "count": 0}
            timeline_map[ts_key]["cpu_total"] += s.cpu_percent
            timeline_map[ts_key]["mem_total"] += s.memory_used_mb
            timeline_map[ts_key]["count"] += 1

        timeline = [
            {
                "timestamp": k,
                "avg_cpu": round(v["cpu_total"] / v["count"], 2) if v["count"] > 0 else 0.0,
                "total_mem_mb": round(v["mem_total"], 2)
            }
            for k, v in list(timeline_map.items())[-20:] # Keep last 20 time slices
        ]

        # Container distribution
        containers_active = docker_service.list_containers(all_containers=True)
        container_dist = [
            {
                "name": c["name"],
                "status": c["status"],
                "cpu_limit": c["cpu_limit"],
                "memory_limit_mb": c["memory_limit_mb"],
                "image": c["image"]
            }
            for c in containers_active
        ]

        # Lifecycle history from ActivityLog
        lifecycle_events = db.query(
            ActivityLog.event_type,
            func.count(ActivityLog.id)
        ).group_by(ActivityLog.event_type).all()
        lifecycle_counts = {evt: cnt for evt, cnt in lifecycle_events}

        return {
            "timeframe": f"Last {timeframe_minutes} Minutes",
            "total_points": total_points,
            "avg_cpu_percent": avg_cpu,
            "peak_cpu_percent": peak_cpu,
            "avg_memory_used_mb": avg_mem,
            "peak_memory_used_mb": peak_mem,
            "timeline": timeline,
            "container_distribution": container_dist,
            "lifecycle_summary": lifecycle_counts
        }

analytics_service = AnalyticsService()
