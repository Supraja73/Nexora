from typing import List, Dict, Any, Optional
from pydantic import BaseModel

class LiveStatsResponse(BaseModel):
    container_id: str
    container_name: str
    status: str
    cpu_percent: float
    cpu_cores_allocated: float
    cpu_quota: Optional[int] = None
    cpu_period: Optional[int] = None
    memory_used_mb: float
    memory_limit_mb: float
    memory_percent: float
    rx_bytes: int
    tx_bytes: int
    rx_human: str
    tx_human: str
    block_read_bytes: int
    block_write_bytes: int
    pids_current: int
    timestamp: str

class MonitoringOverview(BaseModel):
    total_containers: int
    running_containers: int
    stopped_containers: int
    paused_containers: int
    total_active_processes: int
    avg_cpu_percent: float
    total_memory_used_mb: float
    total_memory_limit_mb: float
    overall_memory_percent: float
    docker_status: str
    docker_version: str
    host_os: str
    host_cpu_percent: float
    host_memory_percent: float
    host_total_ram_gb: float
    uptime_seconds: int
    last_updated: str

class HistoricalMetricPoint(BaseModel):
    timestamp: str
    cpu_percent: float
    memory_used_mb: float
    memory_percent: float
    rx_bytes: int
    tx_bytes: int
    pids_count: int

class ContainerHistoryResponse(BaseModel):
    container_id: str
    container_name: str
    points: List[HistoricalMetricPoint]

class AnalyticsOverviewResponse(BaseModel):
    timeframe: str
    total_points: int
    avg_cpu_percent: float
    peak_cpu_percent: float
    avg_memory_used_mb: float
    peak_memory_used_mb: float
    timeline: List[Dict[str, Any]]
    container_distribution: List[Dict[str, Any]]
