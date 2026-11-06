/**
 * NEXORA Main Application Controller
 * Handles SPA navigation, theme switching, notifications, modals, and global timers
 */

class NexoraApp {
  constructor() {
    this.currentView = "view-dashboard";
    this.pollingIntervalMs = parseInt(localStorage.getItem("nexora_polling_interval") || "2000", 10);
    this.pollingTimer = null;
    this.init();
  }

  init() {
    this.setupNavigation();
    this.setupTheme();
    this.setupClock();
    this.setupModals();
    this.setupGlobalActions();
    this.checkDockerStatus();

    // Start background telemetry polling loop
    this.startTelemetryLoop();

    // Re-render Lucide icons
    if (window.lucide) {
      window.lucide.createIcons();
    }
  }

  setupNavigation() {
    const navButtons = document.querySelectorAll("[data-view]");
    navButtons.forEach((btn) => {
      btn.addEventListener("click", (e) => {
        e.preventDefault();
        const targetView = btn.getAttribute("data-view");
        this.switchView(targetView);
      });
    });
  }

  switchView(viewId) {
    if (!document.getElementById(viewId)) return;
    this.currentView = viewId;

    // Update active nav links in sidebar
    document.querySelectorAll(".sidebar-menu .nav-link").forEach((link) => {
      link.classList.toggle("active", link.getAttribute("data-view") === viewId);
    });

    // Update active top navbar tab buttons
    document.querySelectorAll(".top-nav-tabs .top-tab-btn").forEach((btn) => {
      btn.classList.toggle("active", btn.getAttribute("data-view") === viewId);
    });

    // Toggle view sections
    document.querySelectorAll(".view-section").forEach((section) => {
      section.classList.toggle("active", section.id === viewId);
    });

    // Trigger view-specific refreshes
    if (viewId === "view-dashboard" && window.dashboardModule) {
      window.dashboardModule.loadDashboardData();
    } else if (viewId === "view-containers" && window.containersModule) {
      window.containersModule.loadContainers();
    } else if (viewId === "view-processes" && window.processesModule) {
      window.processesModule.refreshProcessesView();
    } else if (viewId === "view-resources" && window.resourcesModule) {
      window.resourcesModule.refreshResourcesView();
    } else if (viewId === "view-monitoring" && window.monitoringModule) {
      window.monitoringModule.refreshMonitoringData();
    } else if (viewId === "view-analytics" && window.analyticsModule) {
      window.analyticsModule.refreshAnalytics();
    } else if (viewId === "view-activity" && window.activityModule) {
      window.activityModule.loadActivities();
    } else if (viewId === "view-settings" && window.settingsModule) {
      window.settingsModule.loadSettingsData();
    }

    if (window.lucide) {
      window.lucide.createIcons();
    }
  }

  setupTheme() {
    const savedTheme = localStorage.getItem("nexora_theme") || "light";
    document.documentElement.setAttribute("data-theme", savedTheme);
    this.updateThemeIcon(savedTheme);

    const toggleBtn = document.getElementById("theme-toggle-btn");
    if (toggleBtn) {
      toggleBtn.addEventListener("click", () => {
        const currentTheme = document.documentElement.getAttribute("data-theme") || "light";
        const newTheme = currentTheme === "light" ? "dark" : "light";
        document.documentElement.setAttribute("data-theme", newTheme);
        localStorage.setItem("nexora_theme", newTheme);
        this.updateThemeIcon(newTheme);
      });
    }
  }

  updateThemeIcon(theme) {
    const iconEl = document.getElementById("theme-icon");
    if (iconEl) {
      iconEl.setAttribute("data-lucide", theme === "dark" ? "sun" : "moon");
      if (window.lucide) window.lucide.createIcons();
    }
  }

  setupClock() {
    const clockEl = document.getElementById("header-clock");
    const updateTime = () => {
      if (clockEl) {
        const now = new Date();
        clockEl.textContent = now.toLocaleTimeString();
      }
    };
    updateTime();
    setInterval(updateTime, 1000);
  }

  setupModals() {
    // Open create container modal
    const openBtns = [document.getElementById("btn-open-create-modal"), document.getElementById("btn-open-create-modal-2")];
    openBtns.forEach((btn) => {
      if (btn) {
        btn.addEventListener("click", () => this.openModal("modal-create-container"));
      }
    });

    // Close buttons
    document.querySelectorAll("[data-close-modal]").forEach((btn) => {
      btn.addEventListener("click", () => {
        const targetModal = btn.getAttribute("data-close-modal");
        this.closeModal(targetModal);
      });
    });

    // Close on backdrop click
    document.querySelectorAll(".modal-backdrop").forEach((backdrop) => {
      backdrop.addEventListener("click", (e) => {
        if (e.target === backdrop) {
          backdrop.classList.remove("active");
        }
      });
    });
  }

  openModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
      modal.classList.add("active");
      if (window.lucide) window.lucide.createIcons();
    }
  }

  closeModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
      modal.classList.remove("active");
    }
  }

  setupGlobalActions() {
    const refreshBtn = document.getElementById("refresh-all-btn");
    if (refreshBtn) {
      refreshBtn.addEventListener("click", () => {
        this.checkDockerStatus();
        this.switchView(this.currentView);
        this.showToast("Refreshed", "Live telemetry and container states updated.", "success");
      });
    }
  }

  async checkDockerStatus() {
    const badge = document.getElementById("header-docker-badge");
    const dot = document.getElementById("header-docker-dot");
    const text = document.getElementById("header-docker-text");

    try {
      const status = await window.api.getDockerStatus();
      if (status.is_connected && status.mode === "live") {
        dot.className = "pulse-dot";
        text.textContent = `Docker Live (${status.engine_version})`;
        badge.title = `Connected to live Docker Engine ${status.engine_version} on ${status.endpoint}`;
      } else {
        dot.className = "pulse-dot fallback";
        text.textContent = "NEXORA Fallback Engine";
        badge.title = status.message;
      }
    } catch (err) {
      dot.className = "pulse-dot stopped";
      text.textContent = "Docker Offline";
      badge.title = "Failed to connect to Docker API";
    }
  }

  startTelemetryLoop() {
    if (this.pollingTimer) clearInterval(this.pollingTimer);
    this.pollingTimer = setInterval(() => {
      // Background poll overview on dashboard or live monitoring
      if (this.currentView === "view-dashboard" && window.dashboardModule) {
        window.dashboardModule.tickLiveTelemetry();
      } else if (this.currentView === "view-monitoring" && window.monitoringModule) {
        window.monitoringModule.tickMonitoring();
      }
    }, this.pollingIntervalMs);
  }

  setPollingInterval(ms) {
    this.pollingIntervalMs = ms;
    localStorage.setItem("nexora_polling_interval", ms.toString());
    this.startTelemetryLoop();
  }

  showToast(title, message, type = "success") {
    const container = document.getElementById("toast-container");
    if (!container) return;

    const toast = document.createElement("div");
    toast.className = `toast ${type}`;

    let iconName = "check-circle-2";
    if (type === "error") iconName = "alert-circle";
    if (type === "warning") iconName = "alert-triangle";

    toast.innerHTML = `
      <i data-lucide="${iconName}" class="toast-icon"></i>
      <div class="toast-content">
        <div class="toast-title">${title}</div>
        <div class="toast-message">${message}</div>
      </div>
    `;

    container.appendChild(toast);
    if (window.lucide) window.lucide.createIcons();

    setTimeout(() => {
      toast.style.opacity = "0";
      toast.style.transform = "translateX(50px)";
      setTimeout(() => toast.remove(), 300);
    }, 4500);
  }
}

window.app = new NexoraApp();
