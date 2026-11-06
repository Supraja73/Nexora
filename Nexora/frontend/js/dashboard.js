/**
 * NEXORA Main Dashboard Module
 * Renders Finexy-inspired live CPU/Memory spline charts, 8 metric cards, and container table
 */

class DashboardModule {
  constructor() {
    this.cpuChart = null;
    this.memChart = null;
    this.maxPoints = 15;
    this.cpuHistory = [];
    this.memHistory = [];
    this.labels = [];
    this.init();
  }

  init() {
    this.initCharts();
    this.loadDashboardData();
  }

  initCharts() {
    const isDark = document.documentElement.getAttribute("data-theme") === "dark";
    const gridColor = isDark ? "rgba(255, 255, 255, 0.05)" : "rgba(0, 0, 0, 0.05)";
    const textColor = isDark ? "#9CA3AF" : "#858585";

    // Chart 1: Live CPU Utilization
    const cpuCtx = document.getElementById("chart-live-cpu");
    if (cpuCtx) {
      const gradient = cpuCtx.getContext("2d").createLinearGradient(0, 0, 0, 220);
      gradient.addColorStop(0, "rgba(165, 240, 68, 0.35)");
      gradient.addColorStop(1, "rgba(165, 240, 68, 0.0)");

      this.cpuChart = new Chart(cpuCtx, {
        type: "line",
        data: {
          labels: this.labels,
          datasets: [
            {
              label: "CPU Usage (%)",
              data: this.cpuHistory,
              borderColor: "#A5F044",
              borderWidth: 2.5,
              backgroundColor: gradient,
              fill: true,
              tension: 0.4,
              pointRadius: 2,
              pointHoverRadius: 5,
            },
          ],
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: { legend: { display: false } },
          scales: {
            x: { grid: { color: gridColor }, ticks: { color: textColor, font: { size: 10 } } },
            y: { min: 0, suggestedMax: 100, grid: { color: gridColor }, ticks: { color: textColor, font: { size: 10 } } },
          },
        },
      });
    }

    // Chart 2: Live Memory Consumption
    const memCtx = document.getElementById("chart-live-memory");
    if (memCtx) {
      const gradient = memCtx.getContext("2d").createLinearGradient(0, 0, 0, 220);
      gradient.addColorStop(0, "rgba(12, 104, 77, 0.4)");
      gradient.addColorStop(1, "rgba(12, 104, 77, 0.0)");

      this.memChart = new Chart(memCtx, {
        type: "line",
        data: {
          labels: this.labels,
          datasets: [
            {
              label: "Memory Used (MB)",
              data: this.memHistory,
              borderColor: "#0C684D",
              borderWidth: 2.5,
              backgroundColor: gradient,
              fill: true,
              tension: 0.4,
              pointRadius: 2,
              pointHoverRadius: 5,
            },
          ],
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: { legend: { display: false } },
          scales: {
            x: { grid: { color: gridColor }, ticks: { color: textColor, font: { size: 10 } } },
            y: { min: 0, suggestedMax: 1024, grid: { color: gridColor }, ticks: { color: textColor, font: { size: 10 } } },
          },
        },
      });
    }
  }

  async loadDashboardData() {
    try {
      await Promise.all([
        this.fetchOverviewMetrics(),
        this.fetchRunningContainers(),
        this.fetchRecentActivities(),
        this.fetchSystemSpecs(),
      ]);
    } catch (err) {
      console.error("Dashboard data load error:", err);
    }
  }

  async fetchOverviewMetrics() {
    const overview = await window.api.getMonitoringOverview();
    
    // Update 8 Metric Cards
    document.getElementById("dash-total-containers").textContent = overview.total_containers;
    document.getElementById("dash-running-containers").textContent = overview.running_containers;
    document.getElementById("dash-stopped-containers").textContent = overview.stopped_containers;
    document.getElementById("dash-cpu-util").textContent = overview.avg_cpu_percent.toFixed(1);
    document.getElementById("dash-mem-util").textContent = overview.total_memory_used_mb.toFixed(0);
    document.getElementById("dash-mem-percent-badge").textContent = `${overview.overall_memory_percent}%`;
    document.getElementById("dash-mem-limit-sub").textContent = `of ${overview.total_memory_limit_mb.toFixed(0)}MB cgroup`;
    document.getElementById("dash-active-procs").textContent = overview.total_active_processes;
    
    // Status & Version
    const statusText = overview.docker_status === "online" ? "Online" : "Fallback Active";
    document.getElementById("dash-docker-status").textContent = statusText;
    document.getElementById("dash-docker-version").textContent = `v${overview.docker_version}`;
    document.getElementById("dash-docker-mode-sub").textContent = overview.docker_status === "online" ? "Live Linux Daemon" : "High-Fidelity Engine";

    // Push into Live Charts
    const timeLabel = new Date().toLocaleTimeString().split(" ")[0];
    this.addChartPoint(timeLabel, overview.avg_cpu_percent, overview.total_memory_used_mb);
  }

  addChartPoint(label, cpuVal, memVal) {
    if (this.labels.length >= this.maxPoints) {
      this.labels.shift();
      this.cpuHistory.shift();
      this.memHistory.shift();
    }
    this.labels.push(label);
    this.cpuHistory.push(cpuVal);
    this.memHistory.push(memVal);

    if (this.cpuChart) this.cpuChart.update("none");
    if (this.memChart) this.memChart.update("none");
  }

  async tickLiveTelemetry() {
    try {
      const overview = await window.api.getMonitoringOverview();
      document.getElementById("dash-cpu-util").textContent = overview.avg_cpu_percent.toFixed(1);
      document.getElementById("dash-mem-util").textContent = overview.total_memory_used_mb.toFixed(0);
      document.getElementById("dash-active-procs").textContent = overview.total_active_processes;
      document.getElementById("dash-mem-percent-badge").textContent = `${overview.overall_memory_percent}%`;
      
      const timeLabel = new Date().toLocaleTimeString().split(" ")[0];
      this.addChartPoint(timeLabel, overview.avg_cpu_percent, overview.total_memory_used_mb);
    } catch (e) {
      // Gracefully ignore temporary network blips during polling
    }
  }

  async fetchRunningContainers() {
    const tbody = document.getElementById("dash-containers-tbody");
    if (!tbody) return;

    try {
      const containers = await window.api.listContainers(true);
      const running = containers.filter((c) => c.status === "running").slice(0, 6);

      if (running.length === 0) {
        tbody.innerHTML = `<tr><td colspan="6" style="text-align: center; padding: 24px; color: var(--text-secondary);">No active containers currently running. Click '+ New Container' to launch one!</td></tr>`;
        return;
      }

      tbody.innerHTML = running
        .map(
          (c) => `
        <tr>
          <td>
            <div class="container-row-meta">
              <div class="container-avatar">${c.name.substring(0, 2).toUpperCase()}</div>
              <div>
                <div class="container-name-text">${c.name}</div>
                <div class="container-subtext">${c.image} • ID: ${c.short_id}</div>
              </div>
            </div>
          </td>
          <td><span class="status-pill ${c.status}">${c.status}</span></td>
          <td>
            <div>${c.cpu_limit} Cores</div>
            <div class="table-progress-bar">
              <div class="table-progress-fill" style="width: ${Math.min(c.cpu_percent, 100)}%;"></div>
            </div>
          </td>
          <td>
            <div>${c.memory_used_mb}MB / ${c.memory_limit_mb}MB</div>
            <div class="table-progress-bar">
              <div class="table-progress-fill" style="width: ${c.memory_percent}%; background: ${c.memory_percent > 85 ? 'var(--status-stopped)' : 'var(--primary-lime)'};"></div>
            </div>
          </td>
          <td><span style="font-size: 12px; color: var(--text-secondary);">${c.uptime.split("T")[0] || "Active"}</span></td>
          <td>
            <div class="table-actions-cell">
              <button class="btn-table-action" onclick="window.containersModule.openInspectModal('${c.id}')" title="Inspect Container">
                <i data-lucide="eye"></i>
              </button>
              <button class="btn-table-action" onclick="window.containersModule.stopContainer('${c.id}')" title="Stop Container">
                <i data-lucide="square"></i>
              </button>
              <button class="btn-table-action" onclick="window.resourcesModule.selectContainerForTuning('${c.id}')" title="Tune Resources">
                <i data-lucide="sliders"></i>
              </button>
            </div>
          </td>
        </tr>
      `
        )
        .join("");

      if (window.lucide) window.lucide.createIcons();
    } catch (err) {
      tbody.innerHTML = `<tr><td colspan="6" style="text-align: center; color: var(--status-stopped); padding: 20px;">Failed to load container data: ${err.message}</td></tr>`;
    }
  }

  async fetchRecentActivities() {
    const stream = document.getElementById("dash-activity-stream");
    if (!stream) return;

    try {
      const data = await window.api.getActivityLogs({ limit: 6 });
      if (!data.items || data.items.length === 0) {
        stream.innerHTML = `<div style="padding: 20px; text-align: center; color: var(--text-secondary);">No logged events yet.</div>`;
        return;
      }

      stream.innerHTML = data.items
        .map((act) => {
          let icon = "activity";
          if (act.event_type === "create") icon = "plus-circle";
          if (act.event_type === "start") icon = "play";
          if (act.event_type === "stop") icon = "square";
          if (act.event_type === "delete") icon = "trash-2";
          if (act.event_type === "resource_update") icon = "sliders";

          return `
          <div class="activity-item">
            <div class="activity-icon"><i data-lucide="${icon}"></i></div>
            <div>
              <div class="activity-desc">${act.description}</div>
              <div class="activity-time">${act.timestamp}</div>
            </div>
          </div>
        `;
        })
        .join("");

      if (window.lucide) window.lucide.createIcons();
    } catch (err) {
      stream.innerHTML = `<div style="padding: 16px; color: var(--status-stopped);">Failed to load activities: ${err.message}</div>`;
    }
  }

  async fetchSystemSpecs() {
    try {
      const sys = await window.api.getSystemInfo();
      document.getElementById("spec-arch").textContent = `${sys.machine} ${sys.platform}`;
      document.getElementById("spec-kernel").textContent = sys.docker_status.kernel_version || `${sys.platform} ${sys.release}`;
      document.getElementById("spec-cgroup").textContent = sys.cgroup_info.version || "cgroups v2";
      document.getElementById("spec-api").textContent = `API ${sys.docker_status.api_version || "1.45"}`;
      document.getElementById("spec-cores").textContent = `${sys.cpu_count} Logical Cores`;
      document.getElementById("spec-ram").textContent = `${(sys.memory_total_mb / 1024).toFixed(1)} GB Total`;
    } catch (e) {
      console.warn("Failed to load system specs", e);
    }
  }
}

window.dashboardModule = new DashboardModule();
