/**
 * NEXORA Analytics & Audit Log Module
 * Time-series analytics from SQLite snapshots and audit trail filtering
 */

class AnalyticsModule {
  constructor() {
    this.selectedTimeframe = 60;
    this.timelineChart = null;
    this.init();
  }

  init() {
    this.initChart();
    this.setupListeners();
  }

  setupListeners() {
    const buttons = document.querySelectorAll(".analytics-tf-btn");
    buttons.forEach((btn) => {
      btn.addEventListener("click", () => {
        buttons.forEach((b) => b.classList.remove("active"));
        btn.classList.add("active");
        this.selectedTimeframe = parseInt(btn.getAttribute("data-minutes"), 10);
        this.refreshAnalytics();
      });
    });
  }

  initChart() {
    const isDark = document.documentElement.getAttribute("data-theme") === "dark";
    const gridColor = isDark ? "rgba(255, 255, 255, 0.05)" : "rgba(0, 0, 0, 0.05)";
    const textColor = isDark ? "#9CA3AF" : "#858585";

    const ctx = document.getElementById("chart-analytics-timeline");
    if (!ctx) return;

    this.timelineChart = new Chart(ctx, {
      type: "line",
      data: {
        labels: [],
        datasets: [
          {
            label: "Average CPU (%)",
            data: [],
            borderColor: "#A5F044",
            backgroundColor: "rgba(165, 240, 68, 0.2)",
            fill: true,
            tension: 0.4,
            yAxisID: "y",
          },
          {
            label: "Aggregate RAM (MB)",
            data: [],
            borderColor: "#0C684D",
            backgroundColor: "rgba(12, 104, 77, 0.25)",
            fill: true,
            tension: 0.4,
            yAxisID: "y1",
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
          x: { grid: { color: gridColor }, ticks: { color: textColor } },
          y: {
            type: "linear",
            display: true,
            position: "left",
            min: 0,
            grid: { color: gridColor },
            ticks: { color: textColor },
            title: { display: true, text: "CPU %", color: textColor },
          },
          y1: {
            type: "linear",
            display: true,
            position: "right",
            min: 0,
            grid: { drawOnChartArea: false },
            ticks: { color: textColor },
            title: { display: true, text: "Memory (MB)", color: textColor },
          },
        },
      },
    });
  }

  async refreshAnalytics() {
    try {
      const data = await window.api.getAnalyticsOverview(this.selectedTimeframe);
      document.getElementById("analytics-avg-cpu").textContent = `${data.avg_cpu_percent}%`;
      document.getElementById("analytics-peak-cpu").textContent = `${data.peak_cpu_percent}%`;
      document.getElementById("analytics-avg-mem").textContent = `${data.avg_memory_used_mb} MB`;
      document.getElementById("analytics-points").textContent = data.total_points;

      if (this.timelineChart && data.timeline) {
        this.timelineChart.data.labels = data.timeline.map((t) => t.timestamp);
        this.timelineChart.data.datasets[0].data = data.timeline.map((t) => t.avg_cpu);
        this.timelineChart.data.datasets[1].data = data.timeline.map((t) => t.total_mem_mb);
        this.timelineChart.update();
      }
    } catch (err) {
      console.error("Analytics fetch error:", err);
    }
  }
}

class ActivityModule {
  constructor() {
    this.init();
  }

  init() {
    const searchInput = document.getElementById("activity-search-input");
    const typeFilter = document.getElementById("activity-type-filter");
    const refreshBtn = document.getElementById("btn-refresh-activities");

    if (searchInput) searchInput.addEventListener("input", () => this.loadActivities());
    if (typeFilter) typeFilter.addEventListener("change", () => this.loadActivities());
    if (refreshBtn) refreshBtn.addEventListener("click", () => this.loadActivities());
  }

  async loadActivities() {
    const tbody = document.getElementById("activity-tbody");
    if (!tbody) return;

    const search = document.getElementById("activity-search-input")?.value.trim() || undefined;
    const eventType = document.getElementById("activity-type-filter")?.value.trim() || undefined;

    try {
      const data = await window.api.getActivityLogs({
        limit: 50,
        search,
        event_type: eventType,
      });

      if (!data.items || data.items.length === 0) {
        tbody.innerHTML = `<tr><td colspan="5" style="text-align: center; padding: 24px; color: var(--text-secondary);">No audit events matching criteria.</td></tr>`;
        return;
      }

      tbody.innerHTML = data.items
        .map((act) => {
          let badgeClass = "created";
          if (act.event_type === "create" || act.event_type === "start" || act.status === "success") badgeClass = "running";
          if (act.event_type === "stop" || act.event_type === "delete") badgeClass = "stopped";
          if (act.event_type === "pause") badgeClass = "paused";

          return `
          <tr>
            <td style="font-family: monospace; font-size: 12px; color: var(--text-secondary);">${act.timestamp}</td>
            <td><span class="status-pill ${badgeClass}">${act.event_type}</span></td>
            <td><strong>${act.container_name || (act.container_id ? act.container_id.substring(0, 12) : "System")}</strong></td>
            <td><span class="status-pill ${act.status === 'success' ? 'running' : 'stopped'}">${act.status}</span></td>
            <td style="color: var(--text-primary); font-size: 13px;">${act.description}</td>
          </tr>
        `;
        })
        .join("");
    } catch (err) {
      tbody.innerHTML = `<tr><td colspan="5" style="text-align: center; color: var(--status-stopped); padding: 20px;">Failed to load audit history: ${err.message}</td></tr>`;
    }
  }
}

window.analyticsModule = new AnalyticsModule();
window.activityModule = new ActivityModule();
