# NEXORA User Guide & Project Demonstration Walkthrough

**Linux Container-Based Process Isolation and Resource Management Platform**

---

## 1. Navigating the Platform

NEXORA features a responsive single-page architecture inspired by the **Finexy** SaaS dashboard design language:
- **Left Sidebar**: Permanent navigation across the 7 functional platform modules.
- **Top Header**: Live Docker status indicator, current system clock, dark/light theme toggle, and the "+ New Container" quick action button.
- **Content Body**: Instantaneous tab switching with zero page reloads.

---

## 2. Main Dashboard Walkthrough

When you access `http://127.0.0.1:8000`:
1. **Welcome Banner**: Displays "Good morning, Administrator" and current isolation state.
2. **8 Metric Cards**:
   - Total Containers, Running Containers, Stopped Containers.
   - CPU Utilization (calculated dynamically across active cgroup allocations).
   - Memory Utilization (actual memory footprint vs cgroup hard limit).
   - Active Processes (sum of virtual PIDs across container hierarchies).
   - Container Health (OOM safety monitoring).
   - Docker Engine Status & Version.
3. **Live Charts**: Real-time spline curves showing CPU % and memory working set consumption.
4. **Running Containers Table**: Instant control actions (Start, Stop, Restart, Pause, Inspect, Tune).
5. **Recent Activity Feed**: Real-time audit logs of container operations.

---

## 3. Container Management

### Creating a Container
1. Click **"+ New Container"** from either the header or the Container Management view.
2. Enter a sanitized name (e.g., `web-service-alpha`).
3. Select an image (`alpine:latest`, `nginx:alpine`, `redis:alpine`, `python:3.12-alpine`, etc.).
4. Adjust the **CPU Limit** slider (0.1 to 4.0 cores) and **Memory Limit** slider (64 MB to 4096 MB).
5. Optionally configure port forwarding (e.g., `8080:80`) and restart policy.
6. Click **Create & Launch Container**.

### Lifecycle Actions
- **Pause / Unpause**: Uses the Linux cgroup freezer to suspend execution of all threads without terminating the process.
- **Stop / Start / Restart**: Gracefully signals container processes with `SIGTERM` followed by `SIGKILL` on timeout.
- **Inspect**: Displays the full kernel configuration, cgroups path (`/sys/fs/cgroup/docker/...`), and networking parameters.
- **Remove**: Deletes container and cleans up associated namespaces.

---

## 4. Demonstrating Process Isolation (College Evaluation Guide)

### Concept: Linux Namespaces vs Virtual Machines
Navigate to **Process Isolation**:
1. Select any running container from the dropdown.
2. Observe the process table:
   - **Container PID**: The container's root process is assigned **PID 1** (`CLONE_NEWPID`).
   - **Host PID**: On the host Linux kernel, this exact same process has an unprivileged PID (e.g., **28415**).
3. **Inter-Container Comparison**:
   - Launch two containers (e.g., `container-a` and `container-b`).
   - Notice that both containers simultaneously run distinct **PID 1** processes.
   - Neither container can enumerate, inspect, or signal processes belonging to the other container.
4. Review the **7 Linux Kernel Namespaces** cards (PID, NET, MNT, IPC, UTS, USER, CGROUP) and the direct comparison table explaining why containers share the host kernel while maintaining strict process isolation.

---

## 5. Demonstrating Resource Management (cgroups Enforcement)

Navigate to **Resource Management**:
1. Select a container.
2. Drag the **CPU Allocation** slider (e.g., from `1.0` to `2.0` cores).
   - Notice the live calculation of `cpu.cfs_quota_us`: $2.0 \times 100{,}000 = 200{,}000\ \mu\text{s}$.
3. Drag the **Memory Maximum** slider (e.g., from `512 MB` to `1024 MB`).
   - Notice the live calculation of `memory.max`: $1{,}073{,}741{,}824\text{ bytes}$.
4. Click **Apply cgroup Limits to Kernel**.
5. The container updates dynamically in real-time via `container.update()` without restarting.
6. If memory usage exceeds $85\%$, the high-utilization alert banner triggers automatically.

---

## 6. Live Monitoring & Telemetry

Navigate to **Live Monitoring**:
- Telemetry updates every 2 seconds.
- **Network I/O**: Tracks cumulative RX and TX bytes across container `veth` interfaces.
- **Resource Footprint**: Bar chart comparing memory allocated vs memory currently consumed.
- **Block I/O**: Disk read and write counters.

---

## 7. Analytics & Audit Log

- **Analytics**: Filter historical data by 15 min, 1 hour, 6 hours, or 24 hours to view average CPU utilization, peak spikes, and timeline curves.
- **Activity Log**: Full filterable audit ledger with search capabilities and status indicators (Success, Failure, Warning).
