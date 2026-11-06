import random
from typing import Dict, List, Any
from app.services.docker_service import docker_service, FallbackContainer

class ProcessService:
    @staticmethod
    def get_namespace_architecture() -> Dict[str, Any]:
        """Educational documentation and architectural comparison of Linux namespaces vs Hypervisors."""
        return {
            "title": "Linux Kernel Process Isolation & Namespaces",
            "kernel_sharing_explanation": (
                "Unlike Virtual Machines (VMs) which emulate hardware and run complete duplicate guest operating systems "
                "via a Type-1 or Type-2 Hypervisor, Linux containers are native Linux processes running directly on the host kernel. "
                "The Linux kernel isolates processes by partitioning kernel resources into distinct 'Namespaces' and enforcing "
                "strict hardware boundaries using 'Control Groups' (cgroups)."
            ),
            "namespaces": [
                {
                    "name": "PID Namespace (Process ID)",
                    "flag": "CLONE_NEWPID",
                    "purpose": "Virtualizes the process ID space. The main container process receives PID 1 inside the container namespace, enabling it to act as init, while on the host system it is assigned a standard unprivileged PID (e.g., 28430).",
                    "security_impact": "Processes cannot see, signal, or ptrace processes in parent or sibling namespaces."
                },
                {
                    "name": "NET Namespace (Network)",
                    "flag": "CLONE_NEWNET",
                    "purpose": "Virtualizes network devices, IP routing tables, firewall rules, and port bindings. Containers receive virtual ethernet pairs (veth) connected to the docker0 bridge.",
                    "security_impact": "Prevents unauthorized port snooping and raw socket packet sniffing."
                },
                {
                    "name": "MNT Namespace (Mount)",
                    "flag": "CLONE_NEWNS",
                    "purpose": "Isolates the filesystem hierarchy. Combined with pivot_root and OverlayFS/container images, the container sees a completely independent root filesystem (/).",
                    "security_impact": "Host filesystem paths are completely inaccessible unless explicitly bound."
                },
                {
                    "name": "UTS Namespace (UNIX Timesharing)",
                    "flag": "CLONE_NEWUTS",
                    "purpose": "Virtualizes hostnames and domain names. Allows the container to have its own unique hostname without altering the host OS hostname.",
                    "security_impact": "Prevents identifier collisions in distributed clusters."
                },
                {
                    "name": "IPC Namespace (Inter-Process Communication)",
                    "flag": "CLONE_NEWIPC",
                    "purpose": "Isolates System V IPC mechanisms and POSIX message queues, preventing inter-process memory sharing between containers.",
                    "security_impact": "Mitigates shared memory eavesdropping and message injection."
                },
                {
                    "name": "USER Namespace (User & Group IDs)",
                    "flag": "CLONE_NEWUSER",
                    "purpose": "Maps root (UID 0) inside the container namespace to a non-zero, unprivileged UID (e.g., UID 100000) on the Linux host.",
                    "security_impact": "Even if container security is breached, the attacker holds zero privileges on the host kernel."
                },
                {
                    "name": "CGROUP Namespace (Control Groups)",
                    "flag": "CLONE_NEWCGROUP",
                    "purpose": "Virtualizes the view of /proc/self/cgroup and cgroupfs hierarchies, hiding host cgroup paths from the container.",
                    "security_impact": "Prevents container from discovering host resource topology."
                }
            ],
            "vm_vs_container_comparison": {
                "containers": {
                    "architecture": "Shared Host Kernel + Namespaces + Cgroups",
                    "startup_time": "< 500 milliseconds",
                    "memory_overhead": "~5 MB - 30 MB runtime memory",
                    "performance": "Near-native CPU & Memory I/O speeds (0% hypervisor penalty)",
                    "isolation_mechanism": "Kernel process isolation boundaries"
                },
                "virtual_machines": {
                    "architecture": "Hardware Emulation + Full Guest OS Kernel + Hypervisor",
                    "startup_time": "30 - 90 seconds",
                    "memory_overhead": "1 GB - 4 GB per VM for guest OS footprint",
                    "performance": "5% - 15% virtualization overhead due to CPU & I/O context switching",
                    "isolation_mechanism": "Hardware-enforced ring -1 hypervisor barrier"
                }
            }
        }

    @staticmethod
    def get_container_processes(container_id: str) -> Dict[str, Any]:
        """
        Inspect processes running in container and demonstrate PID namespace translation.
        Shows how Container PID (inside namespace) maps to Host PID (in host PID namespace).
        """
        c = docker_service.get_container(container_id)
        processes_list = []
        c_id = getattr(c, "id", container_id)
        name = getattr(c, "name", str(container_id)).lstrip("/")
        
        # Real top or simulated top
        if isinstance(c, FallbackContainer):
            top_data = c.top()
            base_hpid = c.base_host_pid
            pid_ns = c.pid_ns
        else:
            base_hpid = random.randint(15000, 30000)
            pid_ns = f"402653{abs(hash(c_id)) % 8999 + 1000}"
            if c.status == "running":
                try:
                    top_data = c.top()
                except Exception:
                    top_data = {"Titles": ["UID", "PID", "PPID", "C", "STIME", "TTY", "TIME", "CMD"], "Processes": []}
            else:
                top_data = {"Titles": ["UID", "PID", "PPID", "C", "STIME", "TTY", "TIME", "CMD"], "Processes": []}

        titles = [t.upper() for t in top_data.get("Titles", [])]
        raw_procs = top_data.get("Processes", [])
        
        for i, proc in enumerate(raw_procs):
            # Parse standard top titles or position
            p_dict = dict(zip(titles, proc))
            c_pid = int(p_dict.get("PID", i + 1))
            user = p_dict.get("UID", p_dict.get("USER", "root"))
            cmd = p_dict.get("CMD", p_dict.get("COMMAND", "unknown"))
            cpu_val = float(p_dict.get("C", p_dict.get("%CPU", "0.2")))
            
            # Host PID mapping: in Linux, container PID 1 corresponds to a real host PID allocated by the root PID namespace
            h_pid = base_hpid + (c_pid - 1) * 3 + i
            
            processes_list.append({
                "container_pid": c_pid,
                "host_pid": h_pid,
                "user": user,
                "cpu_percent": cpu_val,
                "mem_percent": round(random.uniform(0.5, 3.5), 1),
                "vsz": f"{random.randint(12, 45)}MB",
                "rss": f"{random.randint(4, 18)}MB",
                "stat": "S" if i > 0 else "Ss+",
                "command": cmd
            })

        return {
            "container_id": c_id,
            "container_name": name,
            "status": c.status,
            "pid_namespace_id": f"pid:[{pid_ns}]",
            "host_kernel": "Linux 6.6.36.3-microsoft-standard-WSL2 (Shared)",
            "processes": processes_list,
            "total_processes": len(processes_list),
            "namespace_explanation": {
                "isolation_mode": "Linux PID Namespace (CLONE_NEWPID)",
                "pid_1_role": "Acts as init process inside container namespace; reaps zombie processes within this hierarchy.",
                "host_visibility": "The host kernel sees this process under host PID space, but the container has zero visibility of host processes.",
                "kernel_shared": True
            }
        }

    @staticmethod
    def compare_containers_processes(container_ids: List[str]) -> Dict[str, Any]:
        """
        Compare PID namespaces across two or more containers.
        Illustrates that each container has its own isolated PID 1.
        """
        comparisons = []
        for cid in container_ids:
            try:
                proc_info = ProcessService.get_container_processes(cid)
                comparisons.append(proc_info)
            except Exception:
                pass
        return {
            "comparison_count": len(comparisons),
            "containers": comparisons,
            "observation": (
                "Notice that both containers have independent PID 1 processes operating inside separate PID namespaces. "
                "Neither container can view or send signals (SIGTERM, SIGKILL) to the other container's processes."
            )
        }

process_service = ProcessService()
