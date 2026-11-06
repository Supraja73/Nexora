import asyncio
import logging
from datetime import datetime, timedelta
from app.database import SessionLocal
from app.models.models import MetricSnapshot, SystemAlert
from app.services.docker_service import docker_service
from app.config import settings

logger = logging.getLogger("nexora.collector")

class MetricsCollector:
    def __init__(self):
        self.is_running = False
        self._task: asyncio.Task | None = None

    async def start(self):
        """Start background metrics collection loop."""
        if self.is_running:
            return
        self.is_running = True
        self._task = asyncio.create_task(self._collect_loop())
        logger.info("Background metrics collector task started.")

    async def stop(self):
        """Stop background metrics collection loop."""
        self.is_running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Background metrics collector task stopped.")

    async def _collect_loop(self):
        while self.is_running:
            try:
                self.collect_snapshot()
            except Exception as e:
                logger.error(f"Error during metrics collection tick: {e}")
            await asyncio.sleep(settings.MONITORING_INTERVAL_SECONDS)

    def collect_snapshot(self):
        """Collect current metrics from running containers and persist in SQLite."""
        db = SessionLocal()
        try:
            containers = docker_service.list_containers(all_containers=False)
            now = datetime.utcnow()
            for c in containers:
                try:
                    stats = docker_service.get_container_stats(c["id"])
                    snap = MetricSnapshot(
                        timestamp=now,
                        container_id=c["id"],
                        container_name=c["name"],
                        cpu_percent=stats["cpu_percent"],
                        memory_used_mb=stats["memory_used_mb"],
                        memory_limit_mb=stats["memory_limit_mb"],
                        memory_percent=stats["memory_percent"],
                        rx_bytes=stats["rx_bytes"],
                        tx_bytes=stats["tx_bytes"],
                        block_read_bytes=stats["block_read_bytes"],
                        block_write_bytes=stats["block_write_bytes"],
                        pids_count=stats["pids_current"]
                    )
                    db.add(snap)

                    # Trigger alert if memory > 85%
                    if stats["memory_percent"] >= 85.0:
                        alert = SystemAlert(
                            timestamp=now,
                            alert_type="memory_high",
                            severity="warning",
                            message=f"Container {c['name']} memory usage exceeded 85% ({stats['memory_percent']}%)",
                            container_id=c["id"]
                        )
                        db.add(alert)
                except Exception as c_err:
                    logger.debug(f"Could not collect stats for container {c.get('name')}: {c_err}")
            
            # Prune snapshots older than retention period (e.g. 24h)
            retention_cutoff = now - timedelta(hours=settings.METRICS_HISTORY_RETENTION_HOURS)
            db.query(MetricSnapshot).filter(MetricSnapshot.timestamp < retention_cutoff).delete()
            db.commit()
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to save metrics snapshot: {e}")
        finally:
            db.close()

collector = MetricsCollector()
