/**
 * NEXORA Resource Management & cgroups Module
 * Controls CPU CFS quota, memory.max limits, live enforcement metrics and utilization warnings
 */

class ResourcesModule {
  constructor() {
    this.containers = [];
    this.selectedContainerId = null;
    this.init();
  }

  init() {
    this.setupListeners();
  }

  setupListeners() {
    const select = document.getElementById("resource-container-select");
    if (select) {
      select.addEventListener("change", (e) => {
        this.selectedContainerId = e.target.value;
        this.fetchContainerResources(this.selectedContainerId);
      });
    }

    // Dynamic slider live calculations
    const cpuSlider = document.getElementById("resource-cpu-slider");
    const cpuValBadge = document.getElementById("slider-cpu-val");
    const cpuQuotaCalc = document.getElementById("cgroup-cpu-quota-calc");
    if (cpuSlider && cpuValBadge && cpuQuotaCalc) {
      cpuSlider.addEventListener("input", (e) => {
        const val = parseFloat(e.target.value).toFixed(1);
        cpuValBadge.textContent = `${val} Cores`;
        const quota = Math.round(val * 100000);
        cpuQuotaCalc.textContent = `CFS Quota: ${quota.toLocaleString()} µs / 100,000 µs`;
        this.updateKernelPreview();
      });
    }

    const memSlider = document.getElementById("resource-mem-slider");
    const memValBadge = document.getElementById("slider-mem-val");
    const memBytesCalc = document.getElementById("cgroup-mem-bytes-calc");
    if (memSlider && memValBadge && memBytesCalc) {
      memSlider.addEventListener("input", (e) => {
        const val = parseInt(e.target.value, 10);
        memValBadge.textContent = `${val} MB`;
        const bytes = val * 1024 * 1024;
        memBytesCalc.textContent = `memory.max: ${bytes.toLocaleString()} bytes`;
        this.updateKernelPreview();
      });
    }

    // Apply Limits Button
    const applyBtn = document.getElementById("btn-apply-cgroup-resources");
    if (applyBtn) {
      applyBtn.addEventListener("click", () => this.applyResourceLimits());
    }
  }

  async refreshResourcesView() {
    try {
      this.containers = await window.api.listContainers(true);
      const select = document.getElementById("resource-container-select");
      if (!select) return;

      if (this.containers.length === 0) {
        select.innerHTML = `<option value="">No containers found</option>`;
        return;
      }

      select.innerHTML = this.containers
        .map((c) => `<option value="${c.id}">${c.name} (${c.cpu_limit} cores, ${c.memory_limit_mb}MB)</option>`)
        .join("");

      if (!this.selectedContainerId || !this.containers.find((c) => c.id === this.selectedContainerId)) {
        this.selectedContainerId = this.containers[0].id;
      }
      select.value = this.selectedContainerId;

      await this.fetchContainerResources(this.selectedContainerId);
    } catch (err) {
      console.error("Failed to load resources view:", err);
    }
  }

  selectContainerForTuning(containerId) {
    this.selectedContainerId = containerId;
    window.app.switchView("view-resources");
  }

  async fetchContainerResources(containerId) {
    if (!containerId) return;

    try {
      const data = await window.api.getContainerResources(containerId);
      
      // Update sliders
      const cpuSlider = document.getElementById("resource-cpu-slider");
      const cpuValBadge = document.getElementById("slider-cpu-val");
      const cpuQuotaCalc = document.getElementById("cgroup-cpu-quota-calc");

      if (cpuSlider) cpuSlider.value = data.cpu.cores_allocated;
      if (cpuValBadge) cpuValBadge.textContent = `${data.cpu.cores_allocated.toFixed(1)} Cores`;
      if (cpuQuotaCalc) {
        cpuQuotaCalc.textContent = `CFS Quota: ${data.cpu.quota_us.toLocaleString()} µs / ${data.cpu.period_us.toLocaleString()} µs`;
      }

      const memSlider = document.getElementById("resource-mem-slider");
      const memValBadge = document.getElementById("slider-mem-val");
      const memBytesCalc = document.getElementById("cgroup-mem-bytes-calc");

      if (memSlider) memSlider.value = data.memory.limit_mb;
      if (memValBadge) memValBadge.textContent = `${data.memory.limit_mb} MB`;
      if (memBytesCalc) {
        memBytesCalc.textContent = `memory.max: ${data.memory.limit_bytes.toLocaleString()} bytes`;
      }

      // Live metrics readout
      document.getElementById("res-detail-cpu").textContent = `${data.cpu.current_percent.toFixed(1)}%`;
      document.getElementById("res-detail-mem").textContent = `${data.memory.used_mb.toFixed(0)} MB`;
      document.getElementById("res-detail-mem-sub").textContent = `${data.memory.percent.toFixed(1)}% of limit`;

      // Warning banner
      const warningBanner = document.getElementById("resource-warning-banner");
      if (warningBanner) {
        if (data.warning_message) {
          warningBanner.textContent = data.warning_message;
          warningBanner.style.display = "block";
        } else {
          warningBanner.style.display = "none";
        }
      }

      this.updateKernelPreview();
    } catch (err) {
      console.error("Failed to fetch container resources:", err);
    }
  }

  updateKernelPreview() {
    const box = document.getElementById("cgroup-inspect-box");
    if (!box) return;

    const cpuVal = parseFloat(document.getElementById("resource-cpu-slider")?.value || 1.0);
    const memVal = parseInt(document.getElementById("resource-mem-slider")?.value || 512, 10);
    const quota = Math.round(cpuVal * 100000);
    const memBytes = memVal * 1024 * 1024;

    box.innerHTML = `# Active Linux cgroups v2 Virtual Filesystem (/sys/fs/cgroup)
/sys/fs/cgroup/cpu.max: ${quota} 100000  (CFS Quota ${quota}us per 100000us period)
/sys/fs/cgroup/cpu.weight: 100  (Proportional CFS shares)
/sys/fs/cgroup/memory.max: ${memBytes}  (${memVal} MB Hard Boundary)
/sys/fs/cgroup/memory.high: ${Math.round(memBytes * 0.9)}  (Kernel Throttling Threshold)
/sys/fs/cgroup/memory.oom.group: 1  (Atomic OOM Process Eviction)`;
  }

  async applyResourceLimits() {
    if (!this.selectedContainerId) return;
    const btn = document.getElementById("btn-apply-cgroup-resources");
    btn.disabled = true;
    btn.textContent = "Enforcing cgroups limits...";

    const cpuLimit = parseFloat(document.getElementById("resource-cpu-slider").value);
    const memLimit = parseInt(document.getElementById("resource-mem-slider").value, 10);

    try {
      const res = await window.api.updateContainerResources(this.selectedContainerId, cpuLimit, memLimit);
      window.app.showToast("cgroup Limits Updated", `CPU: ${res.cpu_limit} cores, Memory: ${res.memory_limit_mb}MB enforced dynamically.`, "success");
      await this.fetchContainerResources(this.selectedContainerId);
      if (window.dashboardModule) window.dashboardModule.loadDashboardData();
    } catch (err) {
      window.app.showToast("Update Failed", err.message, "error");
    } finally {
      btn.disabled = false;
      btn.innerHTML = `<i data-lucide="check"></i> Apply cgroup Limits to Kernel`;
      if (window.lucide) window.lucide.createIcons();
    }
  }
}

window.resourcesModule = new ResourcesModule();
