/**
 * NEXORA System Settings Module
 * Handles UI preferences, refresh rates, and Docker daemon diagnostics
 */

class SettingsModule {
  constructor() {
    this.init();
  }

  init() {
    this.setupListeners();
    this.loadSettingsData();
  }

  setupListeners() {
    const saveBtn = document.getElementById("btn-save-settings");
    if (saveBtn) {
      saveBtn.addEventListener("click", () => this.savePreferences());
    }

    const reconnectBtn = document.getElementById("btn-reconnect-docker");
    if (reconnectBtn) {
      reconnectBtn.addEventListener("click", () => this.reconnectDocker());
    }
  }

  loadSettingsData() {
    // Populate preferences
    const themeSelect = document.getElementById("settings-theme-select");
    const intervalSelect = document.getElementById("settings-interval-select");

    if (themeSelect) {
      themeSelect.value = localStorage.getItem("nexora_theme") || "light";
    }
    if (intervalSelect) {
      intervalSelect.value = localStorage.getItem("nexora_polling_interval") || "2000";
    }

    this.loadDiagnostics();
  }

  async loadDiagnostics() {
    const diagBox = document.getElementById("settings-docker-diagnostics");
    if (!diagBox) return;

    try {
      const status = await window.api.getDockerStatus();
      diagBox.textContent = JSON.stringify(status, null, 2);
    } catch (err) {
      diagBox.textContent = `Diagnostic error: ${err.message}`;
    }
  }

  savePreferences() {
    const themeSelect = document.getElementById("settings-theme-select");
    const intervalSelect = document.getElementById("settings-interval-select");

    if (themeSelect) {
      const theme = themeSelect.value;
      document.documentElement.setAttribute("data-theme", theme);
      localStorage.setItem("nexora_theme", theme);
      if (window.app) window.app.updateThemeIcon(theme);
    }

    if (intervalSelect) {
      const intervalMs = parseInt(intervalSelect.value, 10);
      if (window.app) window.app.setPollingInterval(intervalMs);
    }

    window.app.showToast("Settings Saved", "Preferences updated and saved locally.", "success");
  }

  async reconnectDocker() {
    const btn = document.getElementById("btn-reconnect-docker");
    btn.disabled = true;
    btn.textContent = "Checking daemon socket...";

    try {
      await window.app.checkDockerStatus();
      await this.loadDiagnostics();
      window.app.showToast("Docker Polled", "Docker daemon connection re-evaluated successfully.", "success");
    } catch (err) {
      window.app.showToast("Connection Error", err.message, "error");
    } finally {
      btn.disabled = false;
      btn.innerHTML = `<i data-lucide="refresh-cw"></i> Reconnect Docker Engine`;
      if (window.lucide) window.lucide.createIcons();
    }
  }
}

window.settingsModule = new SettingsModule();
