# NEXORA — Project Audit

**Audit date:** 6 November 2026  
**Scope:** Uploaded ZIP source snapshot; static inspection plus syntax checks.  
**Verdict:** Development/demo build. Not yet verified as a fully functioning live Linux container manager.

## Checks performed

| Check | Result | Notes |
|---|---|---|
| ZIP/source inspection | Passed | Backend, frontend, docs, tests, Docker files inspected |
| Python syntax compilation | Passed | `compileall` on `backend/app` |
| JavaScript syntax | Passed | `node --check` on all `frontend/js/*.js` |
| Automated pytest suite | Blocked | Import failed because `docker` Python package was not installed; package install could not reach package index |
| Docker Engine integration | Not verified | This environment did not have access to the user's Docker Desktop/WSL Engine |
| Browser end-to-end | Not verified | No live server + Docker Engine session available |
| Screenshot capture | Not performed | A screenshot of a non-running/static UI would not prove functionality |

## Confirmed simulation / fabricated data

### 1. Docker fallback engine

File: `backend/app/services/docker_service.py`

- `FallbackContainer` is explicitly a simulation class.
- `_init_fallback_containers()` creates three pre-populated sample containers:
  - `nexora-web-gateway`
  - `nexora-redis-cache`
  - `nexora-worker-task`
- Random host PIDs, namespace identifiers, network counters, block I/O counters, CPU and memory values are generated.
- Fallback start/stop/restart/pause/unpause/update operations change in-memory Python object state. They do not operate on Linux processes or kernel cgroups.
- `get_status()` returns hardcoded fallback engine/API/kernel/driver/cgroup values when Docker is offline.
- `.env.example` sets `ENABLE_DEMO_FALLBACK=True`.

**Impact:** Dashboard values in fallback mode must not be described as real Docker telemetry or kernel enforcement.

### 2. Process namespace screen

File: `backend/app/services/process_service.py`

- In live mode, the service calls Docker's `container.top()` to obtain a container process list.
- It then synthesizes `host_pid` from a random base PID instead of reading the real host PID mapping.
- It synthesizes the PID namespace inode using a hash of the container ID.
- It generates random `mem_percent`, `vsz`, and `rss` values.
- It hardcodes a WSL kernel string in the response.

**Impact:** The current process view is partly based on a real process list but its host PID mapping, namespace ID, and memory fields are not reliable measurements.

### 3. Frontend static labels

File: `frontend/index.html`

The initial HTML contains fixed text for a WSL 2 host, a specific Linux kernel version, cgroups v2, and “Linux Process Isolation: Active”. These labels can be incorrect on another machine or when Docker is disconnected. Populate them from API data and display an explicit connection state.

### 4. README claims

The original README claimed 100% passing tests, complete live cgroup enforcement, live PID mapping, and a verified high-fidelity platform. Those claims were not supported by the supplied snapshot or this audit. The README has been rewritten to disclose the limitations and verification status.

## Test execution details

Command attempted:

```powershell
cd backend
python -m pytest tests -q
```

Collection failed while importing `app.services.docker_service` because the `docker` Python package was missing (`ModuleNotFoundError: No module named 'docker'`). Installing requirements was attempted, but this environment could not reach the Python package index. Therefore, **no test pass/fail count is claimed**.

## Required fixes before calling it production-like

1. Make live Docker status authoritative and visually prominent.
2. Never show seeded containers or synthetic metrics as live data. Either remove fallback mode or show a persistent `SIMULATION MODE` banner and separate demo endpoints/data.
3. Replace fabricated host PID mapping with actual host PID data obtained from the Linux host/WSL process namespace (or remove the host PID column until implemented).
4. Read namespace inode IDs from the real container process namespace, rather than generating them from a hash.
5. Remove random process memory fields; collect supported real process metrics or show `N/A`.
6. Populate OS/kernel/cgroup labels from the actual Docker Engine and host response.
7. Run tests in a clean Python 3.12 environment and add tests for live/disconnected modes.
8. Verify create/start/stop/pause/update/delete and cgroup values against Docker Engine on WSL 2.
9. Capture GitHub screenshots only after confirming `/api/docker/status` reports `mode: live` and `is_connected: true`.

## Safe screenshot procedure

1. Start Docker Desktop and wait for the engine to be ready.
2. Run `docker ps -a` and note the real containers.
3. Start NEXORA and open `/api/docker/status`.
4. Confirm `mode` is `live` and `is_connected` is `true`.
5. Create or use a disposable test container.
6. Capture dashboard, container list, inspect, resource, and process screens.
7. If the status is fallback/disconnected, do not present those screens as live functionality.
