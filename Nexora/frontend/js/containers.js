/**
 * NEXORA Container Management Module
 * Handles container CRUD, start/stop/restart/pause/unpause, filtering and inspections
 */

class ContainersModule {
  constructor() {
    this.containers = [];
    this.selectedDeleteId = null;
    this.init();
  }

  init() {
    this.setupEventListeners();
    this.loadContainers();
  }

  setupEventListeners() {
    // Search & Filter
    const searchInput = document.getElementById("containers-search-input");
    const statusFilter = document.getElementById("containers-status-filter");
    if (searchInput) searchInput.addEventListener("input", () => this.renderContainersTable());
    if (statusFilter) statusFilter.addEventListener("change", () => this.renderContainersTable());

    const refreshBtn = document.getElementById("btn-refresh-containers");
    if (refreshBtn) refreshBtn.addEventListener("click", () => this.loadContainers());

    // Create Modal Sliders
    const cpuSlider = document.getElementById("create-cpu-slider");
    const cpuBadge = document.getElementById("modal-cpu-badge");
    if (cpuSlider && cpuBadge) {
      cpuSlider.addEventListener("input", (e) => {
        cpuBadge.textContent = `${parseFloat(e.target.value).toFixed(1)} Cores`;
      });
    }

    const memSlider = document.getElementById("create-mem-slider");
    const memBadge = document.getElementById("modal-mem-badge");
    if (memSlider && memBadge) {
      memSlider.addEventListener("input", (e) => {
        memBadge.textContent = `${e.target.value} MB`;
      });
    }

    // Custom Image select toggle
    const imgSelect = document.getElementById("create-image-select");
    const customImgGroup = document.getElementById("create-custom-image-group");
    if (imgSelect && customImgGroup) {
      imgSelect.addEventListener("change", (e) => {
        customImgGroup.style.display = e.target.value === "custom" ? "block" : "none";
      });
    }

    // Create Container Form Submit
    const form = document.getElementById("form-create-container");
    if (form) {
      form.addEventListener("submit", (e) => this.handleCreateContainer(e));
    }

    // Confirm Delete Action
    const confirmDeleteBtn = document.getElementById("btn-confirm-delete-action");
    if (confirmDeleteBtn) {
      confirmDeleteBtn.addEventListener("click", () => this.executeDeleteContainer());
    }
  }

  async loadContainers() {
    const tbody = document.getElementById("containers-tbody");
    if (tbody) {
      tbody.innerHTML = `<tr><td colspan="9" style="text-align: center; padding: 24px;">Fetching container records from Docker Engine...</td></tr>`;
    }

    try {
      this.containers = await window.api.listContainers(true);
      this.renderContainersTable();
    } catch (err) {
      if (tbody) {
        tbody.innerHTML = `<tr><td colspan="9" style="text-align: center; color: var(--status-stopped); padding: 20px;">Failed to load containers: ${err.message}</td></tr>`;
      }
    }
  }

  renderContainersTable() {
    const tbody = document.getElementById("containers-tbody");
    if (!tbody) return;

    const searchTerm = (document.getElementById("containers-search-input")?.value || "").toLowerCase().trim();
    const statusFilter = document.getElementById("containers-status-filter")?.value || "all";

    const filtered = this.containers.filter((c) => {
      const matchesSearch =
        c.name.toLowerCase().includes(searchTerm) ||
        c.id.toLowerCase().includes(searchTerm) ||
        c.image.toLowerCase().includes(searchTerm);
      const matchesStatus = statusFilter === "all" || c.status === statusFilter;
      return matchesSearch && matchesStatus;
    });

    if (filtered.length === 0) {
      tbody.innerHTML = `<tr><td colspan="9" style="text-align: center; padding: 28px; color: var(--text-secondary);">No containers match your search filters.</td></tr>`;
      return;
    }

    tbody.innerHTML = filtered
      .map((c) => {
        const isRunning = c.status === "running";
        const isPaused = c.status === "paused";

        return `
        <tr>
          <td>
            <div class="container-row-meta">
              <div class="container-avatar">${c.name.substring(0, 2).toUpperCase()}</div>
              <div>
                <div class="container-name-text">${c.name}</div>
                <div class="container-subtext">${c.uptime ? c.uptime.split("T")[0] : "Created"}</div>
              </div>
            </div>
          </td>
          <td><code style="background: var(--bg-subtle); padding: 3px 6px; border-radius: 4px; font-size: 11px;">${c.short_id}</code></td>
          <td><span style="font-weight: 500; font-size: 12px;">${c.image}</span></td>
          <td><span class="status-pill ${c.status}">${c.status}</span></td>
          <td>${c.cpu_limit} Cores</td>
          <td>${c.memory_limit_mb} MB</td>
          <td>${c.port_mapping ? `<span class="status-pill created" style="font-family: monospace;">${c.port_mapping}</span>` : '<span style="color:var(--text-muted);">None</span>'}</td>
          <td><span style="font-size: 11px; text-transform: uppercase; color: var(--text-secondary);">${c.restart_policy}</span></td>
          <td>
            <div class="table-actions-cell">
              ${
                isRunning
                  ? `<button class="btn-table-action" onclick="window.containersModule.stopContainer('${c.id}')" title="Stop Container"><i data-lucide="square"></i></button>`
                  : `<button class="btn-table-action" onclick="window.containersModule.startContainer('${c.id}')" title="Start Container"><i data-lucide="play"></i></button>`
              }
              ${
                isPaused
                  ? `<button class="btn-table-action" onclick="window.containersModule.unpauseContainer('${c.id}')" title="Unpause Container"><i data-lucide="play-circle"></i></button>`
                  : isRunning
                  ? `<button class="btn-table-action" onclick="window.containersModule.pauseContainer('${c.id}')" title="Pause Container"><i data-lucide="pause-circle"></i></button>`
                  : ""
              }
              <button class="btn-table-action" onclick="window.containersModule.restartContainer('${c.id}')" title="Restart Container"><i data-lucide="rotate-ccw"></i></button>
              <button class="btn-table-action" onclick="window.containersModule.openInspectModal('${c.id}')" title="Inspect Container"><i data-lucide="info"></i></button>
              <button class="btn-table-action" onclick="window.resourcesModule.selectContainerForTuning('${c.id}')" title="Edit cgroup Limits"><i data-lucide="sliders"></i></button>
              <button class="btn-table-action danger" onclick="window.containersModule.confirmDelete('${c.id}', '${c.name}')" title="Delete Container"><i data-lucide="trash-2"></i></button>
            </div>
          </td>
        </tr>
      `;
      })
      .join("");

    if (window.lucide) window.lucide.createIcons();
  }

  async handleCreateContainer(e) {
    e.preventDefault();
    const btn = document.getElementById("btn-submit-create-container");
    btn.disabled = true;
    btn.textContent = "Creating...";

    const name = document.getElementById("create-name").value.trim();
    let image = document.getElementById("create-image-select").value;
    if (image === "custom") {
      image = document.getElementById("create-custom-image").value.trim();
    }
    const cpuLimit = parseFloat(document.getElementById("create-cpu-slider").value);
    const memLimit = parseInt(document.getElementById("create-mem-slider").value, 10);
    const portMap = document.getElementById("create-ports").value.trim() || null;
    const restartPolicy = document.getElementById("create-restart-policy").value;

    try {
      const payload = {
        name,
        image,
        cpu_limit: cpuLimit,
        memory_limit_mb: memLimit,
        port_mapping: portMap,
        restart_policy: restartPolicy,
      };

      const result = await window.api.createContainer(payload);
      window.app.showToast("Container Created", `Container '${result.name}' successfully launched.`, "success");
      window.app.closeModal("modal-create-container");
      document.getElementById("form-create-container").reset();
      
      // Refresh views
      await this.loadContainers();
      if (window.dashboardModule) window.dashboardModule.loadDashboardData();
    } catch (err) {
      window.app.showToast("Creation Failed", err.message, "error");
    } finally {
      btn.disabled = false;
      btn.innerHTML = `<i data-lucide="play"></i> Create & Launch Container`;
      if (window.lucide) window.lucide.createIcons();
    }
  }

  async startContainer(id) {
    try {
      await window.api.startContainer(id);
      window.app.showToast("Container Started", `Container ${id.substring(0, 12)} is now running.`, "success");
      await this.loadContainers();
      if (window.dashboardModule) window.dashboardModule.loadDashboardData();
    } catch (err) {
      window.app.showToast("Start Failed", err.message, "error");
    }
  }

  async stopContainer(id) {
    try {
      await window.api.stopContainer(id);
      window.app.showToast("Container Stopped", `Container ${id.substring(0, 12)} was stopped.`, "success");
      await this.loadContainers();
      if (window.dashboardModule) window.dashboardModule.loadDashboardData();
    } catch (err) {
      window.app.showToast("Stop Failed", err.message, "error");
    }
  }

  async restartContainer(id) {
    try {
      await window.api.restartContainer(id);
      window.app.showToast("Container Restarted", `Container ${id.substring(0, 12)} was restarted.`, "success");
      await this.loadContainers();
      if (window.dashboardModule) window.dashboardModule.loadDashboardData();
    } catch (err) {
      window.app.showToast("Restart Failed", err.message, "error");
    }
  }

  async pauseContainer(id) {
    try {
      await window.api.pauseContainer(id);
      window.app.showToast("Container Paused", `Processes frozen via cgroup freezer.`, "warning");
      await this.loadContainers();
      if (window.dashboardModule) window.dashboardModule.loadDashboardData();
    } catch (err) {
      window.app.showToast("Pause Failed", err.message, "error");
    }
  }

  async unpauseContainer(id) {
    try {
      await window.api.unpauseContainer(id);
      window.app.showToast("Container Resumed", `Processes resumed execution.`, "success");
      await this.loadContainers();
      if (window.dashboardModule) window.dashboardModule.loadDashboardData();
    } catch (err) {
      window.app.showToast("Resume Failed", err.message, "error");
    }
  }

  confirmDelete(id, name) {
    this.selectedDeleteId = id;
    document.getElementById("delete-container-name").textContent = name;
    window.app.openModal("modal-confirm-delete");
  }

  async executeDeleteContainer() {
    if (!this.selectedDeleteId) return;
    const cid = this.selectedDeleteId;
    window.app.closeModal("modal-confirm-delete");

    try {
      await window.api.removeContainer(cid, true);
      window.app.showToast("Container Removed", `Container ${cid.substring(0, 12)} deleted successfully.`, "success");
      this.selectedDeleteId = null;
      await this.loadContainers();
      if (window.dashboardModule) window.dashboardModule.loadDashboardData();
    } catch (err) {
      window.app.showToast("Removal Failed", err.message, "error");
    }
  }

  async openInspectModal(id) {
    window.app.openModal("modal-inspect-container");
    const jsonBox = document.getElementById("inspect-json-box");
    jsonBox.textContent = "Inspecting container metadata and cgroups configuration...";

    try {
      const details = await window.api.inspectContainer(id);
      document.getElementById("inspect-modal-title").textContent = `Inspection: ${details.name} (${details.image})`;
      jsonBox.textContent = JSON.stringify(details, null, 2);
    } catch (err) {
      jsonBox.textContent = `Error inspecting container: ${err.message}`;
    }
  }
}

window.containersModule = new ContainersModule();
