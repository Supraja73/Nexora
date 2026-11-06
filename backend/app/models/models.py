from datetime import datetime
from sqlalchemy import Column, Integer, BigInteger, Float, String, Text, Boolean, DateTime
from app.database import Base

class ContainerRecord(Base):
    __tablename__ = "container_records"

    id = Column(Integer, primary_key=True, index=True)
    container_id = Column(String(64), unique=True, index=True, nullable=False)
    name = Column(String(128), index=True, nullable=False)
    image = Column(String(256), nullable=False)
    status = Column(String(32), default="created")  # running, exited, paused, created
    cpu_limit = Column(Float, default=1.0)          # Number of cores / nano_cpus / 1e9
    memory_limit_mb = Column(Integer, default=512)  # In MB
    port_mappings = Column(String(256), default="") # e.g. "8080:80"
    restart_policy = Column(String(32), default="no")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class MetricSnapshot(Base):
    __tablename__ = "metric_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    container_id = Column(String(64), index=True, nullable=False)
    container_name = Column(String(128), nullable=False)
    cpu_percent = Column(Float, default=0.0)
    memory_used_mb = Column(Float, default=0.0)
    memory_limit_mb = Column(Float, default=0.0)
    memory_percent = Column(Float, default=0.0)
    rx_bytes = Column(BigInteger, default=0)
    tx_bytes = Column(BigInteger, default=0)
    block_read_bytes = Column(BigInteger, default=0)
    block_write_bytes = Column(BigInteger, default=0)
    pids_count = Column(Integer, default=1)

class ActivityLog(Base):
    __tablename__ = "activity_logs"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    event_type = Column(String(64), nullable=False) # create, start, stop, restart, pause, unpause, delete, resource_update, error
    container_id = Column(String(64), nullable=True, index=True)
    container_name = Column(String(128), nullable=True)
    description = Column(Text, nullable=False)
    status = Column(String(32), default="success")  # success, failure, warning, info
    details_json = Column(Text, nullable=True)

class SystemAlert(Base):
    __tablename__ = "system_alerts"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    alert_type = Column(String(64), nullable=False) # memory_high, cpu_high, container_crashed, docker_offline
    severity = Column(String(32), default="warning") # warning, critical, info
    message = Column(Text, nullable=False)
    container_id = Column(String(64), nullable=True)
    acknowledged = Column(Boolean, default=False)
