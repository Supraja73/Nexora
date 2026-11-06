/**
 * NEXORA Process Isolation & Linux Namespaces Module
 * Demonstrates virtual PID hierarchies, host PID mapping, and educational namespace cards
 */

class ProcessesModule {
  constructor() {
    this.containers = [];
    this.selectedContainerId = null;
    this.init();
  }

  init() {
    this.setupListeners();
    this.loadNamespacesGuide();
  }

  setupListeners() {
    const select = document.getElementById("process-container-select");
    if (select) {
      select.addEventListener("change", (e) => {
        this.selectedContainerId = e.target.value;
        this.fetchContainerProcesses(this.selectedContainerId);
      });
    }
  }

  async refreshProcessesView() {
    try {
      this.containers = await window.api.listContainers(false); // get running containers
      const select = document.getElementById("process-container-select");
      if (!select) return;

      if (this.containers.length === 0) {
        select.innerHTML = `<option value="">No running containers</option>`;
        document.getElementById("processes-tbody").innerHTML = `<tr><td colspan="7" style="text-align: center; padding: 24px; color: var(--text-secondary);">Start a container to inspect its isolated PID hierarchy.</td></tr>`;
        document.getElementById("compare-containers-grid").innerHTML = `<div style="grid-column: 1 / -1; padding: 16px; text-align: center; color: var(--text-secondary);">Need at least 2 running containers to demonstrate inter-container comparison.</div>`;
        return;
      }

      select.innerHTML = this.containers
        .map((c) => `<option value="${c.id}">${c.name} (${c.image})</option>`)
        .join("");

      if (!this.selectedContainerId || !this.containers.find((c) => c.id === this.selectedContainerId)) {
        this.selectedContainerId = this.containers[0].id;
      }
      select.value = this.selectedContainerId;

      await this.fetchContainerProcesses(this.selectedContainerId);
      await this.renderInterContainerComparison();
    } catch (err) {
      console.error("Failed to load processes view:", err);
    }
  }

  async fetchContainerProcesses(containerId) {
    const tbody = document.getElementById("processes-tbody");
    const countBadge = document.getElementById("process-count-badge");
    const nsBadge = document.getElementById("process-container-ns-badge");

    if (!containerId) return;

    try {
      const data = await window.api.getContainerProcesses(containerId);
      if (nsBadge) nsBadge.textContent = `Namespace: ${data.pid_namespace_id}`;
      if (countBadge) countBadge.textContent = `${data.total_processes} Active Processes`;

      if (!data.processes || data.processes.length === 0) {
        tbody.innerHTML = `<tr><td colspan="7" style="text-align: center; padding: 20px;">No active processes reported.</td></tr>`;
        return;
      }

      tbody.innerHTML = data.processes
        .map(
          (p) => `
        <tr>
          <td><span class="status-pill running" style="font-family: monospace; font-weight: 700;">PID ${p.container_pid}</span></td>
          <td><span style="font-family: monospace; font-weight: 600; color: var(--secondary-emerald);">${p.host_pid}</span></td>
          <td><code>${p.user}</code></td>
          <td>${p.cpu_percent}%</td>
          <td>${p.mem_percent}%</td>
          <td><span class="status-pill created" style="font-family: monospace;">${p.stat}</span></td>
          <td><code style="background: var(--bg-subtle); padding: 4px 8px; border-radius: 4px; font-size: 12px; color: var(--text-primary);">${p.command}</code></td>
        </tr>
      `
        )
        .join("");

      if (window.lucide) window.lucide.createIcons();
    } catch (err) {
      tbody.innerHTML = `<tr><td colspan="7" style="text-align: center; color: var(--status-stopped); padding: 20px;">Failed to inspect container processes: ${err.message}</td></tr>`;
    }
  }

  async renderInterContainerComparison() {
    const compGrid = document.getElementById("compare-containers-grid");
    if (!compGrid) return;

    const running = this.containers.filter((c) => c.status === "running");
    if (running.length < 2) {
      compGrid.innerHTML = `
        <div style="grid-column: 1 / -1; padding: 18px; background: var(--bg-card); border: 1px solid var(--border-color); border-radius: var(--radius-md); text-align: center; color: var(--text-secondary);">
          Launch at least two containers to compare their independent PID namespaces side-by-side.
        </div>
      `;
      return;
    }

    try {
      const c1 = await window.api.getContainerProcesses(running[0].id);
      const c2 = await window.api.getContainerProcesses(running[1].id);

      compGrid.innerHTML = `
        <div class="section-card" style="padding: 18px;">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
            <strong style="font-size: 14px;">${c1.container_name}</strong>
            <span class="status-pill running" style="font-family: monospace;">${c1.pid_namespace_id}</span>
          </div>
          <p style="font-size: 12px; color: var(--text-secondary); margin-bottom: 12px;">Root process inside container namespace:</p>
          <div class="code-box">
            Container PID: 1<br>
            Host Kernel PID: ${c1.processes[0]?.host_pid || 'N/A'}<br>
            Command: ${c1.processes[0]?.command || 'sh'}
          </div>
        </div>

        <div class="section-card" style="padding: 18px;">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
            <strong style="font-size: 14px;">${c2.container_name}</strong>
            <span class="status-pill running" style="font-family: monospace;">${c2.pid_namespace_id}</span>
          </div>
          <p style="font-size: 12px; color: var(--text-secondary); margin-bottom: 12px;">Root process inside container namespace:</p>
          <div class="code-box">
            Container PID: 1<br>
            Host Kernel PID: ${c2.processes[0]?.host_pid || 'N/A'}<br>
            Command: ${c2.processes[0]?.command || 'sh'}
          </div>
        </div>
      `;
    } catch (e) {
      console.warn("Failed to render comparison", e);
    }
  }

  async loadNamespacesGuide() {
    const container = document.getElementById("namespace-cards-container");
    if (!container) return;

    try {
      const arch = await window.api.getNamespaceArchitecture();
      container.innerHTML = arch.namespaces
        .map(
          (ns) => `
        <div class="namespace-card">
          <span class="namespace-tag">${ns.flag}</span>
          <h4>${ns.name}</h4>
          <p>${ns.purpose}</p>
          <div class="namespace-impact">
            <strong>Isolation Impact:</strong> ${ns.security_impact}
          </div>
        </div>
      `
        )
        .join("");
    } catch (e) {
      console.warn("Failed to load namespace guide", e);
    }
  }
}

window.processesModule = new ProcessesModule();
