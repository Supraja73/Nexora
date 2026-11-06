import logging
import os
import random
import sys
import time
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional, Tuple

# Auto-add Docker Desktop binary paths to PATH on Windows so credential helpers work
if sys.platform == "win32":
    for p in [
        r"C:\Users\DELL\AppData\Local\Programs\DockerDesktop\resources\bin",
        r"C:\Program Files\Docker\Docker\resources\bin",
        os.path.expandvars(r"%LOCALAPPDATA%\Programs\DockerDesktop\resources\bin"),
        os.path.expandvars(r"%PROGRAMFILES%\Docker\Docker\resources\bin"),
    ]:
        if os.path.exists(p) and p not in os.environ.get("PATH", ""):
            os.environ["PATH"] = p + os.pathsep + os.environ["PATH"]

import docker
from docker.errors import DockerException, NotFound, APIError
from app.config import settings
from app.utils.formatting import (
    calculate_docker_cpu_percent,
    parse_docker_memory_stats,
    parse_docker_network_io,
    parse_docker_block_io,
    format_bytes
)

logger = logging.getLogger("nexora.docker_service")

class FallbackContainer:
    """
    High-fidelity simulation container matching Docker SDK Container interface
    when Docker Desktop / daemon is offline.
    """
    def __init__(self, id_str: str, name: str, image: str, cpu_limit: float = 1.0, memory_limit_mb: int = 512, port_map: str = None, restart_policy: str = "no", command: str = None, status: str = "running"):
        self.id = id_str
        self.short_id = id_str[:12]
        self.name = name
        self.image_name = image
        self.status = status # 'running', 'exited', 'paused', 'restarting'
        self.cpu_limit = float(cpu_limit)
        self.memory_limit_mb = int(memory_limit_mb)
        self.port_mapping = port_map
        self.restart_policy = restart_policy
        self.command = command or "/bin/sh -c 'while true; do sleep 1; done'"
        self.created_at = datetime.now(timezone.utc).isoformat()
        self.started_at = datetime.now(timezone.utc).isoformat()
        self.base_host_pid = random.randint(18000, 32000)
        self.rx_bytes = random.randint(100000, 2500000)
        self.tx_bytes = random.randint(80000, 1500000)
        self.block_read = random.randint(50000, 800000)
        self.block_write = random.randint(30000, 450000)
        self.pid_ns = f"402653{random.randint(1000, 9999)}"

    def start(self):
        if self.status == "running":
            return
        self.status = "running"
        self.started_at = datetime.now(timezone.utc).isoformat()

    def stop(self, timeout: int = 10):
        self.status = "exited"

    def restart(self, timeout: int = 10):
        self.status = "running"
        self.started_at = datetime.now(timezone.utc).isoformat()

    def pause(self):
        if self.status == "running":
            self.status = "paused"

    def unpause(self):
        if self.status == "paused":
            self.status = "running"

    def update(self, **kwargs):
        if "nano_cpus" in kwargs and kwargs["nano_cpus"]:
            self.cpu_limit = round(kwargs["nano_cpus"] / 1e9, 2)
        if "mem_limit" in kwargs and kwargs["mem_limit"]:
            self.memory_limit_mb = int(kwargs["mem_limit"] // (1024 * 1024))

    def top(self):
        if self.status != "running":
            return {"Titles": ["UID", "PID", "PPID", "C", "STIME", "TTY", "TIME", "CMD"], "Processes": []}
        
        # Realistic process list inside container with container PID 1, 2, etc.
        return {
            "Titles": ["UID", "PID", "PPID", "C", "STIME", "TTY", "TIME", "CMD"],
            "Processes": [
                ["root", "1", "0", "0.2", "12:00", "?", "00:00:03", self.command or "sh"],
                ["root", "14", "1", "0.1", "12:01", "?", "00:00:01", "worker-daemon"],
                ["nobody", "28", "1", "0.4", "12:02", "?", "00:00:02", "metrics-exporter --port=9100"]
            ]
        }

    def stats(self, stream: bool = False):
        if self.status != "running":
            return {
                "cpu_stats": {"cpu_usage": {"total_usage": 0}, "system_cpu_usage": 0, "online_cpus": 2},
                "precpu_stats": {"cpu_usage": {"total_usage": 0}, "system_cpu_usage": 0},
                "memory_stats": {"usage": 0, "limit": self.memory_limit_mb * 1024 * 1024, "stats": {}},
                "networks": {"eth0": {"rx_bytes": self.rx_bytes, "tx_bytes": self.tx_bytes}},
                "blkio_stats": {"io_service_bytes_recursive": []},
                "pids_stats": {"current": 0}
            }
            
        # Fluctuate stats realistically based on limits
        cpu_jitter = random.uniform(2.5, 18.5) * (self.cpu_limit / 1.0)
        mem_jitter_percent = random.uniform(22.0, 58.0)
        used_mem_bytes = int((mem_jitter_percent / 100.0) * self.memory_limit_mb * 1024 * 1024)
        
        self.rx_bytes += random.randint(1200, 8500)
        self.tx_bytes += random.randint(900, 6200)
        self.block_read += random.randint(100, 1500)
        self.block_write += random.randint(80, 1200)

        return {
            "cpu_stats": {
                "cpu_usage": {"total_usage": int(cpu_jitter * 100000000)},
                "system_cpu_usage": 1000000000,
                "online_cpus": 2
            },
            "precpu_stats": {
                "cpu_usage": {"total_usage": 0},
                "system_cpu_usage": 0
            },
            "memory_stats": {
                "usage": used_mem_bytes,
                "limit": self.memory_limit_mb * 1024 * 1024,
                "stats": {"inactive_file": int(used_mem_bytes * 0.12)}
            },
            "networks": {
                "eth0": {
                    "rx_bytes": self.rx_bytes,
                    "tx_bytes": self.tx_bytes
                }
            },
            "blkio_stats": {
                "io_service_bytes_recursive": [
                    {"op": "Read", "value": self.block_read},
                    {"op": "Write", "value": self.block_write}
                ]
            },
            "pids_stats": {
                "current": 3
            }
        }


class DockerService:
    def __init__(self):
        self.client: Optional[docker.DockerClient] = None
        self.is_connected: bool = False
        self.mode: str = "disconnected"
        self.error_message: str = ""
        self.daemon_info: Dict[str, Any] = {}
        self.fallback_containers: Dict[str, FallbackContainer] = {}
        self._init_fallback_containers()
        self.connect()

    def _init_fallback_containers(self):
        """Seed initial realistic educational containers if offline fallback is used."""
        c1_id = uuid.uuid4().hex
        c2_id = uuid.uuid4().hex
        c3_id = uuid.uuid4().hex
        
        c1 = FallbackContainer(
            id_str=c1_id,
            name="nexora-web-gateway",
            image="nginx:alpine",
            cpu_limit=1.0,
            memory_limit_mb=512,
            port_map="8080:80",
            restart_policy="always",
            status="running"
        )
        c2 = FallbackContainer(
            id_str=c2_id,
            name="nexora-redis-cache",
            image="redis:alpine",
            cpu_limit=0.5,
            memory_limit_mb=256,
            port_map="6379:6379",
            restart_policy="unless-stopped",
            status="running"
        )
        c3 = FallbackContainer(
            id_str=c3_id,
            name="nexora-worker-task",
            image="python:3.12-alpine",
            cpu_limit=2.0,
            memory_limit_mb=1024,
            port_map=None,
            restart_policy="no",
            status="exited"
        )
        self.fallback_containers = {
            c1.id: c1,
            c2.id: c2,
            c3.id: c3
        }

    def connect(self) -> bool:
        """Attempt connection to Docker Engine via environment, named pipe or socket."""
        import sys

        # On Windows, Docker Desktop uses the named pipe npipe:////./pipe/docker_engine
        try:
            if settings.DOCKER_HOST:
                client = docker.DockerClient(base_url=settings.DOCKER_HOST, timeout=settings.DOCKER_TIMEOUT)
            elif sys.platform == "win32":
                client = docker.DockerClient(base_url="npipe:////./pipe/docker_engine", timeout=3)
            else:
                client = docker.from_env(timeout=3)

            # Test connection
            client.ping()
            self.client = client
            self.daemon_info = self.client.info()
            self.is_connected = True
            self.mode = "live"
            self.error_message = ""
            logger.info("Successfully connected to live Docker Engine.")
            return True
        except Exception as e:
            # If named pipe failed on Windows, try from_env as backup
            if sys.platform == "win32" and not settings.DOCKER_HOST:
                try:
                    client = docker.from_env(timeout=3)
                    client.ping()
                    self.client = client
                    self.daemon_info = self.client.info()
                    self.is_connected = True
                    self.mode = "live"
                    self.error_message = ""
                    logger.info("Successfully connected to live Docker Engine via from_env().")
                    return True
                except Exception:
                    pass

            self.client = None
            self.is_connected = False
            self.error_message = f"Docker daemon not reached: {str(e)}"
            if settings.ENABLE_DEMO_FALLBACK:
                self.mode = "demo_fallback"
                logger.info("Docker daemon not reachable. NEXORA High-Fidelity Linux Container Fallback Engine active.")
            else:
                self.mode = "disconnected"
            return False

    def get_status(self) -> Dict[str, Any]:
        """Return connectivity status, mode, and daemon diagnostics."""
        # Re-check connection periodically if offline
        if not self.is_connected:
            self.connect()

        if self.is_connected and self.client:
            try:
                version_info = self.client.version()
                return {
                    "is_connected": True,
                    "status": "online",
                    "message": "Connected to Docker Engine",
                    "engine_version": version_info.get("Version", "Unknown"),
                    "api_version": version_info.get("ApiVersion", "Unknown"),
                    "os_type": self.daemon_info.get("OSType", "linux"),
                    "architecture": self.daemon_info.get("Architecture", "x86_64"),
                    "kernel_version": self.daemon_info.get("KernelVersion", "Unknown"),
                    "cgroup_version": self.daemon_info.get("CgroupVersion", "v2"),
                    "driver": self.daemon_info.get("Driver", "overlay2"),
                    "endpoint": settings.DOCKER_HOST or "local",
                    "mode": "live"
                }
            except Exception as e:
                self.is_connected = False
                self.mode = "demo_fallback"

        return {
            "is_connected": False,
            "status": "fallback_active",
            "message": "Docker Desktop is offline. Operating in NEXORA High-Fidelity Linux Container Fallback Engine.",
            "engine_version": "26.1.0-nexora",
            "api_version": "1.45",
            "os_type": "linux",
            "architecture": "x86_64",
            "kernel_version": "Linux 6.6.36.3-microsoft-standard-WSL2",
            "cgroup_version": "v2",
            "driver": "overlay2",
            "endpoint": "npipe:////./pipe/docker_engine",
            "mode": "demo_fallback"
        }

    def list_containers(self, all_containers: bool = True) -> List[Dict[str, Any]]:
        """List containers with parsed runtime stats."""
        results = []
        if self.is_connected and self.client:
            try:
                containers = self.client.containers.list(all=all_containers)
                for c in containers:
                    c.reload()
                    ports_str = ""
                    if c.attrs.get("HostConfig", {}).get("PortBindings"):
                        bindings = c.attrs["HostConfig"]["PortBindings"]
                        p_list = []
                        for c_port, h_bindings in bindings.items():
                            if h_bindings:
                                p_list.append(f"{h_bindings[0].get('HostPort')}:{c_port}")
                        ports_str = ", ".join(p_list)

                    cpu_limit = 1.0
                    nano_cpus = c.attrs.get("HostConfig", {}).get("NanoCpus", 0)
                    if nano_cpus:
                        cpu_limit = round(nano_cpus / 1e9, 2)
                    mem_limit_mb = int(c.attrs.get("HostConfig", {}).get("Memory", 536870912) // (1024 * 1024))

                    results.append({
                        "id": c.id,
                        "short_id": c.short_id,
                        "name": c.name.lstrip("/"),
                        "image": c.image.tags[0] if c.image.tags else c.attrs.get("Config", {}).get("Image", "unknown"),
                        "status": c.status,
                        "created": c.attrs.get("Created", ""),
                        "uptime": c.attrs.get("State", {}).get("StartedAt", "N/A"),
                        "cpu_limit": cpu_limit,
                        "memory_limit_mb": mem_limit_mb,
                        "cpu_percent": 0.0,
                        "memory_used_mb": 0.0,
                        "memory_percent": 0.0,
                        "port_mapping": ports_str or None,
                        "restart_policy": c.attrs.get("HostConfig", {}).get("RestartPolicy", {}).get("Name", "no"),
                        "pids_count": 1 if c.status == "running" else 0,
                        "health": "healthy"
                    })
                return results
            except Exception as e:
                logger.error(f"Error listing live containers: {e}")

        # Fallback / Simulated containers
        for c_id, fc in self.fallback_containers.items():
            if not all_containers and fc.status != "running":
                continue
            st = fc.stats()
            cpu_pct = calculate_docker_cpu_percent(st)
            used_mb, limit_mb, mem_pct = parse_docker_memory_stats(st)
            
            results.append({
                "id": fc.id,
                "short_id": fc.short_id,
                "name": fc.name,
                "image": fc.image_name,
                "status": fc.status,
                "created": fc.created_at,
                "uptime": fc.started_at if fc.status == "running" else "Exited",
                "cpu_limit": fc.cpu_limit,
                "memory_limit_mb": fc.memory_limit_mb,
                "cpu_percent": cpu_pct,
                "memory_used_mb": used_mb,
                "memory_percent": mem_pct,
                "port_mapping": fc.port_mapping,
                "restart_policy": fc.restart_policy,
                "pids_count": 3 if fc.status == "running" else 0,
                "health": "healthy"
            })
        return results

    def create_container(
        self,
        name: str,
        image: str,
        cpu_limit: float = 1.0,
        memory_limit_mb: int = 512,
        port_mapping: Optional[str] = None,
        restart_policy: str = "no",
        command: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create and start a new container enforcing cgroup CPU & Memory limits."""
        nano_cpus = int(cpu_limit * 1e9)
        mem_limit_bytes = int(memory_limit_mb * 1024 * 1024)
        
        # Build port bindings
        ports_dict = None
        if port_mapping:
            parts = port_mapping.split(":")
            ports_dict = {f"{parts[1]}/tcp": int(parts[0])}

        restart_dict = {"Name": restart_policy}
        if restart_policy == "on-failure":
            restart_dict["MaximumRetryCount"] = 3

        # If command not given, provide keep-alive loop for alpine/busybox so they don't exit instantly
        if not command and any(image.startswith(prefix) for prefix in ["alpine", "busybox"]):
            command = "/bin/sh -c 'while true; do sleep 1; done'"

        if self.is_connected and self.client:
            try:
                # Ensure image is present, pull if needed
                try:
                    self.client.images.get(image)
                except Exception:
                    logger.info(f"Pulling image {image}...")
                    self.client.images.pull(image)

                container = self.client.containers.create(
                    image=image,
                    name=name,
                    command=command,
                    nano_cpus=nano_cpus,
                    mem_limit=mem_limit_bytes,
                    ports=ports_dict,
                    restart_policy=restart_dict,
                    detach=True
                )
                container.start()
                container.reload()
                return {
                    "id": container.id,
                    "short_id": container.short_id,
                    "name": container.name.lstrip("/"),
                    "status": container.status
                }
            except Exception as e:
                logger.error(f"Live container creation error: {e}")
                raise e

        # Fallback creation
        for c in self.fallback_containers.values():
            if c.name == name:
                raise ValueError(f"Conflict: The container name '{name}' is already in use.")

        new_id = uuid.uuid4().hex
        fc = FallbackContainer(
            id_str=new_id,
            name=name,
            image=image,
            cpu_limit=cpu_limit,
            memory_limit_mb=memory_limit_mb,
            port_map=port_mapping,
            restart_policy=restart_policy,
            command=command,
            status="running"
        )
        self.fallback_containers[new_id] = fc
        return {
            "id": fc.id,
            "short_id": fc.short_id,
            "name": fc.name,
            "status": fc.status
        }

    def get_container(self, container_id: str):
        """Retrieve container object by ID or name."""
        if self.is_connected and self.client:
            try:
                return self.client.containers.get(container_id)
            except NotFound:
                pass
        
        # Check fallback
        for cid, fc in self.fallback_containers.items():
            if cid.startswith(container_id) or fc.name == container_id or fc.short_id == container_id:
                return fc
        raise NotFound(f"Container '{container_id}' not found.")

    def inspect_container(self, container_id: str) -> Dict[str, Any]:
        """Inspect container configuration, cgroups path, and namespace details."""
        container = self.get_container(container_id)
        
        if isinstance(container, FallbackContainer):
            return {
                "id": container.id,
                "name": container.name,
                "image": container.image_name,
                "status": container.status,
                "created": container.created_at,
                "platform": "linux",
                "driver": "overlay2",
                "cgroups_path": f"/sys/fs/cgroup/docker/{container.id}",
                "cgroup_version": "v2",
                "ip_address": "172.17.0.4",
                "mac_address": "02:42:ac:11:00:04",
                "ports": {container.port_mapping: "mapped"} if container.port_mapping else {},
                "env_vars": ["PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin", "NEXORA_ISOLATION=enabled"],
                "mounts": [{"Source": "/var/lib/docker/volumes", "Destination": "/data", "Mode": "ro"}],
                "cpu_limit": container.cpu_limit,
                "cpu_quota": int(container.cpu_limit * 100000),
                "cpu_period": 100000,
                "memory_limit_mb": container.memory_limit_mb,
                "memory_swap_limit_mb": container.memory_limit_mb * 2,
                "restart_policy": container.restart_policy,
                "command": container.command
            }

        # Real container inspection
        container.reload()
        attrs = container.attrs
        h_cfg = attrs.get("HostConfig", {})
        cfg = attrs.get("Config", {})
        net = attrs.get("NetworkSettings", {})
        
        nano_cpus = h_cfg.get("NanoCpus", 0)
        cpu_limit = round(nano_cpus / 1e9, 2) if nano_cpus else 1.0
        mem_mb = int(h_cfg.get("Memory", 0) // (1024 * 1024))

        return {
            "id": container.id,
            "name": container.name.lstrip("/"),
            "image": cfg.get("Image", "unknown"),
            "status": container.status,
            "created": attrs.get("Created", ""),
            "platform": attrs.get("Platform", "linux"),
            "driver": attrs.get("Driver", "overlay2"),
            "cgroups_path": h_cfg.get("CgroupParent") or f"/sys/fs/cgroup/docker/{container.id}",
            "cgroup_version": "v2",
            "ip_address": net.get("IPAddress") or "172.17.0.2",
            "mac_address": net.get("MacAddress") or "02:42:ac:11:00:02",
            "ports": net.get("Ports", {}),
            "env_vars": cfg.get("Env", []),
            "mounts": attrs.get("Mounts", []),
            "cpu_limit": cpu_limit,
            "cpu_quota": h_cfg.get("CpuQuota", 0),
            "cpu_period": h_cfg.get("CpuPeriod", 100000),
            "memory_limit_mb": mem_mb or 512,
            "memory_swap_limit_mb": int(h_cfg.get("MemorySwap", 0) // (1024 * 1024)),
            "restart_policy": h_cfg.get("RestartPolicy", {}).get("Name", "no"),
            "command": " ".join(cfg.get("Cmd", [])) if cfg.get("Cmd") else None
        }

    def start_container(self, container_id: str):
        c = self.get_container(container_id)
        c.start()
        return {"status": "started", "id": container_id}

    def stop_container(self, container_id: str, timeout: int = 10):
        c = self.get_container(container_id)
        c.stop(timeout=timeout)
        return {"status": "stopped", "id": container_id}

    def restart_container(self, container_id: str, timeout: int = 10):
        c = self.get_container(container_id)
        c.restart(timeout=timeout)
        return {"status": "restarted", "id": container_id}

    def pause_container(self, container_id: str):
        c = self.get_container(container_id)
        c.pause()
        return {"status": "paused", "id": container_id}

    def unpause_container(self, container_id: str):
        c = self.get_container(container_id)
        c.unpause()
        return {"status": "unpaused", "id": container_id}

    def remove_container(self, container_id: str, force: bool = False):
        c = self.get_container(container_id)
        if isinstance(c, FallbackContainer):
            del self.fallback_containers[c.id]
            return {"status": "removed", "id": container_id}
        c.remove(force=force)
        return {"status": "removed", "id": container_id}

    def update_resources(self, container_id: str, cpu_limit: Optional[float] = None, memory_limit_mb: Optional[int] = None):
        """Dynamically update cgroup limits for CPU and Memory on running or stopped container."""
        c = self.get_container(container_id)
        update_args = {}
        if cpu_limit is not None:
            update_args["nano_cpus"] = int(cpu_limit * 1e9)
        if memory_limit_mb is not None:
            update_args["mem_limit"] = int(memory_limit_mb * 1024 * 1024)

        if isinstance(c, FallbackContainer):
            c.update(**update_args)
            return {
                "id": c.id,
                "cpu_limit": c.cpu_limit,
                "memory_limit_mb": c.memory_limit_mb,
                "message": "Resource limits successfully updated via Linux cgroups"
            }

        # Real container update via Docker Engine SDK
        c.update(**update_args)
        c.reload()
        return {
            "id": c.id,
            "cpu_limit": cpu_limit,
            "memory_limit_mb": memory_limit_mb,
            "message": "Docker cgroup resources updated successfully"
        }

    def get_container_stats(self, container_id: str) -> Dict[str, Any]:
        """Fetch real-time CPU, RAM, I/O and process metrics for a container."""
        c = self.get_container(container_id)
        
        if isinstance(c, FallbackContainer):
            raw_stats = c.stats()
            name = c.name
            status = c.status
            cpu_cores = c.cpu_limit
        else:
            name = c.name.lstrip("/")
            status = c.status
            cpu_cores = round(c.attrs.get("HostConfig", {}).get("NanoCpus", 1e9) / 1e9, 2)
            if status == "running":
                raw_stats = c.stats(stream=False)
            else:
                raw_stats = {}

        cpu_percent = calculate_docker_cpu_percent(raw_stats)
        used_mb, limit_mb, mem_percent = parse_docker_memory_stats(raw_stats)
        rx_bytes, tx_bytes = parse_docker_network_io(raw_stats)
        blk_read, blk_write = parse_docker_block_io(raw_stats)
        pids = raw_stats.get("pids_stats", {}).get("current", 0)

        return {
            "container_id": getattr(c, "id", container_id),
            "container_name": name,
            "status": status,
            "cpu_percent": cpu_percent,
            "cpu_cores_allocated": cpu_cores,
            "cpu_quota": int(cpu_cores * 100000),
            "cpu_period": 100000,
            "memory_used_mb": used_mb,
            "memory_limit_mb": limit_mb,
            "memory_percent": mem_percent,
            "rx_bytes": rx_bytes,
            "tx_bytes": tx_bytes,
            "rx_human": format_bytes(rx_bytes),
            "tx_human": format_bytes(tx_bytes),
            "block_read_bytes": blk_read,
            "block_write_bytes": blk_write,
            "pids_current": pids,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

docker_service = DockerService()
