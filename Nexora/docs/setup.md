# NEXORA Local Installation & Execution Guide (Windows)

This document provides step-by-step instructions to set up and run NEXORA on a local Windows machine using **PowerShell**, **VS Code**, **Docker Desktop**, and **WSL 2**.

---

## Prerequisites Checklist

- Windows 10 (Version 2004 or higher, Build 19041+) or Windows 11
- Administrator access to PowerShell
- Python 3.12+ 64-bit

---

## Step 1: Install WSL 2 (Windows Subsystem for Linux)

Open **PowerShell as Administrator** and execute:

```powershell
# Enable WSL and install the default Ubuntu distribution
wsl --install

# If WSL is already installed, ensure WSL 2 is the default version:
wsl --set-default-version 2

# Verify installation status
wsl --status
```

*Note: Restart your computer if prompted by Windows.*

---

## Step 2: Set Up Ubuntu Linux Distribution

After restarting, open PowerShell or launch Ubuntu from the Start Menu:

```powershell
# Launch Ubuntu
wsl -d Ubuntu

# Inside Ubuntu, update the package list
sudo apt update && sudo apt upgrade -y

# Exit Ubuntu and return to PowerShell
exit
```

---

## Step 3: Install & Configure Docker Desktop

1. Download **Docker Desktop for Windows** from [docker.com/products/docker-desktop](https://www.docker.com/products/docker-desktop/).
2. Run the installer and ensure the option **"Use WSL 2 instead of Hyper-V (recommended)"** is checked.
3. Once installed, start Docker Desktop from the Start Menu.
4. Go to **Settings (Gear Icon) -> General** and verify:
   - `Use the WSL 2 based engine` is **Enabled**.
5. Go to **Settings -> Resources -> WSL Integration**:
   - Check `Enable integration with my default WSL distro`.
   - Turn on the toggle for `Ubuntu`.
   - Click **Apply & restart**.
6. Verify Docker connectivity in PowerShell:

```powershell
docker --version
docker info
```

---

## Step 4: Open Workspace in VS Code

```powershell
cd C:\Users\DELL\Desktop\Nexora
code .
```

Recommended VS Code extensions:
- **Python** (by Microsoft)
- **WSL** (by Microsoft)
- **Docker** (by Microsoft)

---

## Step 5: Create Python Virtual Environment

In your project directory (`Nexora`), create and activate a Python virtual environment:

```powershell
# Create virtual environment
python -m venv venv

# Activate virtual environment in PowerShell
.\venv\Scripts\Activate.ps1

# (If script execution is blocked, enable RemoteSigned scripts)
# Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

---

## Step 6: Install Python Dependencies

```powershell
# Upgrade pip
python -m pip install --upgrade pip

# Install all backend requirements
pip install -r backend/requirements.txt
```

---

## Step 7: Run Automated Verification Tests

Execute the comprehensive test suite to verify health endpoints, container operations, cgroups quotas, and process isolation:

```powershell
# Run pytest from the backend folder
cd backend
python -m pytest tests -v
cd ..
```

*Expected output: All 8 test suites passing (100% pass rate).*

---

## Step 8: Start NEXORA Application

Start the unified FastAPI server:

```powershell
# From the project root with venv active
cd backend
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

---

## Step 9: Access the Web Dashboard

Open your web browser and navigate to:

- **Web Dashboard:** [http://127.0.0.1:8000](http://127.0.0.1:8000)
- **Interactive Swagger API Documentation:** [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **ReDoc Documentation:** [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)

---

## Step 10: Docker Integration Verification

1. On the NEXORA dashboard, click **"+ New Container"**.
2. Create a container named `demo-gateway` using image `nginx:alpine` with `1.0 Core` and `512 MB`.
3. Open Docker Desktop or run in PowerShell:
   ```powershell
   docker ps
   ```
4. Confirm `demo-gateway` appears in Docker Desktop with identical container ID and active status.
