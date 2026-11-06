<div align="center">

# NEXORA

### Linux Container-Based Process Isolation & Resource Management

**Isolate. Monitor. Optimize.**

[![Python](https://img.shields.io/badge/Python-3.12+-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-API-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Docker](https://img.shields.io/badge/Docker-SDK-2496ED?logo=docker&logoColor=white)](https://docker-py.readthedocs.io/)
[![Frontend](https://img.shields.io/badge/Frontend-Vanilla%20JS-F7DF1E?logo=javascript&logoColor=black)](https://developer.mozilla.org/en-US/docs/Web/JavaScript)

</div>

NEXORA is a local web application for exploring and managing Linux containers. It combines a FastAPI backend, a vanilla JavaScript dashboard, Docker Engine integration, and SQLite-based activity/metrics storage.

> **Important accuracy note:** NEXORA currently contains an offline demonstration fallback. When Docker is unavailable, that fallback creates simulated containers and synthetic CPU, memory, I/O, and process information. Those values are **not live host or kernel measurements**. The process namespace screen also currently synthesizes host-PID mappings and namespace identifiers rather than reading the actual host PID namespace. Do not use fallback-mode screenshots or metrics as evidence of real container isolation or cgroup enforcement.

## What is implemented

- FastAPI REST API for container listing, creation, inspection, lifecycle actions, and resource updates.
- Docker SDK integration intended to communicate with a local Docker Engine.
- Dashboard and navigation built with HTML, CSS, and vanilla JavaScript.
- Resource-limit controls that call Docker's container update API in live Docker mode.
- Container statistics parsing for CPU, memory, network I/O, block I/O, and PID counts.
- SQLite models and services for activity records, metric snapshots, and alerts.
- Educational explanations of Linux namespaces and cgroups.
- Pytest test files and Docker deployment files are included; test execution and deployment have not yet been independently verified.

## Current verification status

This repository has been statically inspected. Python source files compile and frontend JavaScript files pass Node.js syntax checks. The automated test suite could **not** be executed in the inspection environment because the Python Docker SDK dependency was unavailable and package installation could not reach the package index.

See [`docs/PROJECT_AUDIT.md`](docs/PROJECT_AUDIT.md) for the findings and limitations. Treat the project as a development/demo build until it has been tested against a running Docker Engine on your machine.

## Screenshots

Add screenshots captured from your own running instance after connecting Docker Desktop and confirming that the UI is in **Live** mode.

Suggested files:

| File | What to capture |
|---|---|
| `docs/screenshots/dashboard.png` | Dashboard with Docker status visibly showing Live/Connected |
| `docs/screenshots/containers.png` | Container list containing containers that actually exist in Docker |
| `docs/screenshots/container-inspect.png` | Inspection details for a real container |
| `docs/screenshots/resources.png` | CPU and memory limits read from a real container |
| `docs/screenshots/processes.png` | Process view, after correcting/validating host PID and namespace data |

Do not upload screenshots that show demo fallback data as real telemetry. If you include a fallback-mode screenshot, label it clearly as **SIMULATION MODE**.

## Architecture

```text
Browser (HTML / CSS / Vanilla JavaScript)
                 |
                 | HTTP / JSON
                 v
          FastAPI application
                 |
       +---------+----------+
       |         |          |
       v         v          v
   Docker SDK  Services   SQLite
       |
       v
 Docker Engine
 (Linux containers / WSL 2 backend)
```

## Technology stack

| Layer | Technology |
|---|---|
| Frontend | HTML5, CSS3, Vanilla JavaScript |
| Charts / icons | Chart.js, Lucide |
| Backend | Python, FastAPI, Uvicorn, Pydantic |
| Container integration | Docker SDK for Python |
| Host metrics | psutil |
| Persistence | SQLite, SQLAlchemy |
| Tests | pytest, FastAPI TestClient |

## Project structure

```text
NEXORA/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── database.py
│   │   ├── routes/
│   │   ├── schemas/
│   │   ├── services/
│   │   ├── monitoring/
│   │   ├── models/
│   │   └── utils/
│   ├── tests/
│   └── requirements.txt
├── frontend/
│   ├── index.html
│   ├── css/
│   ├── js/
│   └── assets/
├── docker/
│   ├── Dockerfile
│   └── docker-compose.yml
├── docs/
│   ├── architecture.md
│   ├── setup.md
│   ├── user-guide.md
│   ├── PROJECT_AUDIT.md
│   └── screenshots/
├── .env.example
├── .gitignore
└── README.md
```

## Run locally on Windows 10/11

### Prerequisites

1. Install Python 3.12.
2. Install Docker Desktop.
3. Enable the WSL 2 backend in Docker Desktop.
4. Start Docker Desktop and wait until its engine is running.
5. Install Git and Visual Studio Code.

Verify Docker from PowerShell:

```powershell
docker version
docker info
```

Both commands should return server/engine information. If the Docker server section is missing, start or repair Docker Desktop before continuing.

### Setup

Open the extracted project folder in VS Code. In the VS Code terminal (PowerShell), run:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r backend/requirements.txt
Copy-Item .env.example .env
```

If PowerShell blocks activation, run:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

Review `.env`. For a genuine Docker-backed run, keep Docker Desktop running. The current `.env.example` enables the demo fallback; understand that it can display synthetic data when Docker is unreachable.

### Start the backend

```powershell
cd backend
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Open:

- Application: http://127.0.0.1:8000
- API documentation: http://127.0.0.1:8000/docs
- Health endpoint: http://127.0.0.1:8000/api/health

Keep the terminal open while using the application. Stop the server with `Ctrl+C`.

### Verify the connection

Check Docker directly:

```powershell
docker ps -a
```

Then open the NEXORA Docker status endpoint:

```text
http://127.0.0.1:8000/api/docker/status
```

Confirm the response reports `mode: "live"` and `is_connected: true` before treating container metrics as real. If it reports `demo_fallback` or `fallback_active`, displayed container/telemetry values may be simulated.

## API overview

The interactive Swagger UI at `/docs` is the authoritative endpoint reference. Main route groups include:

- `/api/containers` — list and create containers; lifecycle and inspection routes.
- `/api/containers/{container_id}/stats` — container telemetry.
- `/api/containers/{container_id}/resources` — read/update resource limits.
- `/api/containers/{container_id}/processes` — process listing.
- `/api/processes/architecture` — educational namespace information.
- `/api/docker/status` — Docker connection status.
- `/api/system/info` — host and Docker information.
- `/api/health` — health check.

## Tests

From the project root, activate the virtual environment and run:

```powershell
cd backend
python -m pytest tests -v
```

Do not claim that all tests pass until this command completes successfully on your machine. The tests may require a working dependency installation and should be run in a clean environment.

## Known limitations to address

- Offline fallback currently seeds demonstration containers and generates synthetic telemetry.
- The process view fabricates host PID mappings, namespace IDs, and several process memory values even when it obtains a real container process list. These are not verified host namespace measurements.
- Some UI labels contain fixed WSL/Linux kernel and “active” status text; they should be populated from the actual API response.
- The current test suite has not been verified end-to-end in this repository snapshot.
- Docker Engine integration, cgroup version reporting, and live resource enforcement must be validated on the target Linux/WSL 2 Docker host.

## Safety

NEXORA can start, stop, restart, pause, update, and delete containers. Use a development Docker environment and disposable containers while testing. Review image and port settings before creating containers. Do not expose the Docker daemon socket or this management API to an untrusted network.

## License

No license file was included in the supplied project archive. Add a `LICENSE` file only after choosing the license you intend to apply.
