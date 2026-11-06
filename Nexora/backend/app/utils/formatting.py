from typing import Dict, Any, Tuple
from datetime import datetime, timezone

def format_bytes(bytes_value: int | float) -> str:
    """Format bytes into human-friendly strings (B, KB, MB, GB)."""
    if bytes_value is None or bytes_value < 0:
        return "0 B"
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_value < 1024.0:
            return f"{bytes_value:.1f} {unit}" if unit != 'B' else f"{int(bytes_value)} B"
        bytes_value /= 1024.0
    return f"{bytes_value:.2f} PB"

def calculate_docker_cpu_percent(stats: Dict[str, Any]) -> float:
    """
    Compute precise Docker CPU utilization percentage across cores using standard Docker CLI formula:
    cpu_delta = cpu_stats.cpu_usage.total_usage - precpu_stats.cpu_usage.total_usage
    system_delta = cpu_stats.system_cpu_usage - precpu_stats.system_cpu_usage
    number_cpus = online_cpus or len(percpu_usage)
    cpu_percent = (cpu_delta / system_delta) * number_cpus * 100.0
    """
    try:
        cpu_stats = stats.get("cpu_stats", {})
        precpu_stats = stats.get("precpu_stats", {})
        
        cpu_usage = cpu_stats.get("cpu_usage", {}).get("total_usage", 0)
        precpu_usage = precpu_stats.get("cpu_usage", {}).get("total_usage", 0)
        cpu_delta = cpu_usage - precpu_usage
        
        system_cpu = cpu_stats.get("system_cpu_usage", 0)
        system_precpu = precpu_stats.get("system_cpu_usage", 0)
        system_delta = system_cpu - system_precpu
        
        online_cpus = cpu_stats.get("online_cpus")
        if not online_cpus:
            percpu = cpu_stats.get("cpu_usage", {}).get("percpu_usage")
            online_cpus = len(percpu) if percpu else 1
            
        if system_delta > 0.0 and cpu_delta > 0.0:
            cpu_percent = (cpu_delta / system_delta) * online_cpus * 100.0
            return round(min(cpu_percent, 100.0 * online_cpus), 2)
    except Exception:
        pass
    return 0.0

def parse_docker_memory_stats(stats: Dict[str, Any]) -> Tuple[float, float, float]:
    """
    Extract (used_mb, limit_mb, percent) from Docker memory stats.
    Memory usage in Linux cgroups v1 / v2 usually includes cache/inactive_file.
    Correct usage = usage - inactive_file (or stats.cache).
    """
    try:
        memory_stats = stats.get("memory_stats", {})
        usage = memory_stats.get("usage", 0)
        limit = memory_stats.get("limit", 1)
        
        # Check cache or inactive_file to adjust working set
        stats_detail = memory_stats.get("stats", {})
        cache = stats_detail.get("inactive_file", stats_detail.get("cache", 0))
        used_bytes = max(0, usage - cache) if usage >= cache else usage
        
        used_mb = round(used_bytes / (1024 * 1024), 2)
        limit_mb = round(limit / (1024 * 1024), 2)
        percent = round((used_bytes / limit) * 100.0, 2) if limit > 0 else 0.0
        return used_mb, limit_mb, min(percent, 100.0)
    except Exception:
        return 0.0, 0.0, 0.0

def parse_docker_network_io(stats: Dict[str, Any]) -> Tuple[int, int]:
    """Calculate aggregate RX and TX bytes across all container virtual ethernet interfaces."""
    rx_bytes = 0
    tx_bytes = 0
    networks = stats.get("networks", {})
    if networks:
        for net_name, net_data in networks.items():
            rx_bytes += net_data.get("rx_bytes", 0)
            tx_bytes += net_data.get("tx_bytes", 0)
    return rx_bytes, tx_bytes

def parse_docker_block_io(stats: Dict[str, Any]) -> Tuple[int, int]:
    """Calculate aggregate block I/O read and write bytes."""
    read_bytes = 0
    write_bytes = 0
    blkio = stats.get("blkio_stats", {})
    io_service_bytes = blkio.get("io_service_bytes_recursive", []) or []
    for item in io_service_bytes:
        op = item.get("op", "").lower()
        val = item.get("value", 0)
        if op == "read":
            read_bytes += val
        elif op == "write":
            write_bytes += val
    return read_bytes, write_bytes
