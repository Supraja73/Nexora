/**
 * NEXORA Live Monitoring Module
 * Streaming multi-container telemetry, Network I/O, Block I/O, and comparative graphs
 */

class MonitoringModule {
  constructor() {
    this.netChart = null;
    this.compareChart = null;
    this.containers = [];
    this.init();
  }

  init() {
    this.initCharts();
  }

  initCharts() {
    const isDark = document.documentElement.getAttribute("data-theme") === "dark";
    const gridColor = isDark ? "rgba(255, 255, 255, 0.05)" : "rgba(0, 0, 0, 0.05)";
    const textColor = isDark ? "#9CA3AF" : "#858585";

    // Chart 1: Network RX / TX line chart
    const netCtx = document.getElementById("chart-net-io");
    if (netCtx) {
      this.netChart = new Chart(netCtx, {
        type: "line",
        data: {
          labels: [],
          datasets: [
            {
              label: "Network RX (KB)",
              data: [],
              borderColor: "#A5F044",
              backgroundColor: "rgba(165, 240, 68, 0.2)",
              tension: 0.3,
              fill: true,
            },
            {
              label: "Network TX (KB)",
              data: [],
              borderColor: "#0C684D",
              backgroundColor: "rgba(12, 104, 77, 0.2)",
              tension: 0.3,
              fill: true,
            },
          ],
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          scales: {
            x: { grid: { color: gridColor }, ticks: { color: textColor } },
            y: { grid: { color: gridColor }, ticks: { color: textColor } },
          },
        },
      });
    }

    // Chart 2: Container Memory comparison bar chart
    const compCtx = document.getElementById("chart-container-compare");
    if (compCtx) {
      this.compareChart = new Chart(compCtx, {
        type: "bar",
        data: {
          labels: [],
          datasets: [
            {
              label: "Memory Allocated (MB)",
              data: [],
              backgroundColor: "rgba(165, 240, 68, 0.8)",
              borderRadius: 6,
            },
            {
              label: "Memory Used (MB)",
              data: [],
              backgroundColor: "rgba(12, 104, 77, 0.85)",
              borderRadius: 6,
            },
          ],
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          scales: {
            x: { grid: { color: gridColor }, ticks: { color: textColor } },
            y: { grid: { color: gridColor }, ticks: { color: textColor } },
          },
        },
      });
    }
  }

  async refreshMonitoringData() {
    await this.collectLiveStats();
  }

  async tickMonitoring() {
    await this.collectLiveStats();
  }

  async collectLiveStats() {
    const tbody = document.getElementById("monitoring-stats-tbody");
    if (!tbody) return;

    try {
      this.containers = await window.api.listContainers(true);
      const running = this.containers.filter((c) => c.status === "running");

      if (running.length === 0) {
        tbody.innerHTML = `<tr><td colspan="7" style="text-align: center; padding: 24px; color: var(--text-secondary);">No running containers to stream telemetry.</td></tr>`;
        return;
      }

      // Fetch stats for all running containers
      const statsPromises = running.map((c) => window.api.getContainerStats(c.id).catch(() => null));
      const statsResults = (await Promise.all(statsPromises)).filter(Boolean);

      tbody.innerHTML = statsResults
        .map(
          (s) => `
        <tr>
          <td>
            <div class="container-row-meta">
              <div class="container-avatar">${s.container_name.substring(0, 2).toUpperCase()}</div>
              <div>
                <strong style="color: var(--text-primary);">${s.container_name}</strong>
                <div class="container-subtext">${s.status}</div>
              </div>
            </div>
          </td>
          <td><strong>${s.cpu_percent.toFixed(1)}%</strong></td>
          <td>${s.memory_used_mb} MB / ${s.memory_limit_mb} MB</td>
          <td>
            <span class="status-pill ${s.memory_percent > 85 ? 'stopped' : 'running'}">
              ${s.memory_percent.toFixed(1)}%
            </span>
          </td>
          <td><span style="font-family: monospace;">RX: ${s.rx_human} | TX: ${s.tx_human}</span></td>
          <td><span style="font-family: monospace;">R: ${s.block_read_bytes}B | W: ${s.block_write_bytes}B</span></td>
          <td><span class="status-pill created">PID Count: ${s.pids_current}</span></td>
        </tr>
      `
        )
        .join("");

      // Update comparison chart
      if (this.compareChart && statsResults.length > 0) {
        this.compareChart.data.labels = statsResults.map((s) => s.container_name);
        this.compareChart.data.datasets[0].data = statsResults.map((s) => s.memory_limit_mb);
        this.compareChart.data.datasets[1].data = statsResults.map((s) => s.memory_used_mb);
        this.compareChart.update("none");
      }

      // Update Network I/O chart
      if (this.netChart && statsResults.length > 0) {
        const timeLabel = new Date().toLocaleTimeString().split(" ")[0];
        const totalRxKb = Math.round(statsResults.reduce((acc, curr) => acc + curr.rx_bytes, 0) / 1024);
        const totalTxKb = Math.round(statsResults.reduce((acc, curr) => acc + curr.tx_bytes, 0) / 1024);

        if (this.netChart.data.labels.length > 12) {
          this.netChart.data.labels.shift();
          this.netChart.data.datasets[0].data.shift();
          this.netChart.data.datasets[1].data.shift();
        }

        this.netChart.data.labels.push(timeLabel);
        this.netChart.data.datasets[0].data.push(totalRxKb);
        this.netChart.data.datasets[1].data.push(totalTxKb);
        this.netChart.update("none");
      }
    } catch (err) {
      console.warn("Failed to collect live monitoring stats", err);
    }
  }
}

window.monitoringModule = new MonitoringModule();
