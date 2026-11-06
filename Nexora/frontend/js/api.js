/**
 * NEXORA Central API Client
 * Clean REST communication layer with error handling and typing
 */

const API_BASE = "";

class NexoraAPI {
  async request(endpoint, options = {}) {
    const config = {
      headers: {
        "Content-Type": "application/json",
        ...options.headers,
      },
      ...options,
    };

    try {
      const response = await fetch(`${API_BASE}${endpoint}`, config);
      const data = await response.json();
      
      if (!response.ok) {
        const errorMsg = data.detail || (typeof data === "string" ? data : "An unexpected server error occurred.");
        throw new Error(errorMsg);
      }
      return data;
    } catch (err) {
      console.error(`API Error [${endpoint}]:`, err);
      throw err;
    }
  }

  // Health & System
  getHealth() {
    return this.request("/api/health");
  }

  getSystemInfo() {
    return this.request("/api/system/info");
  }

  getDockerStatus() {
    return this.request("/api/docker/status");
  }

  // Container Management
  listContainers(all = true) {
    return this.request(`/api/containers?all=${all}`);
  }

  createContainer(payload) {
    return this.request("/api/containers", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  }

  inspectContainer(id) {
    return this.request(`/api/containers/${id}`);
  }

  startContainer(id) {
    return this.request(`/api/containers/${id}/start`, { method: "POST" });
  }

  stopContainer(id, timeout = 10) {
    return this.request(`/api/containers/${id}/stop?timeout=${timeout}`, { method: "POST" });
  }

  restartContainer(id, timeout = 10) {
    return this.request(`/api/containers/${id}/restart?timeout=${timeout}`, { method: "POST" });
  }

  pauseContainer(id) {
    return this.request(`/api/containers/${id}/pause`, { method: "POST" });
  }

  unpauseContainer(id) {
    return this.request(`/api/containers/${id}/unpause`, { method: "POST" });
  }

  removeContainer(id, force = false) {
    return this.request(`/api/containers/${id}?force=${force}`, { method: "DELETE" });
  }

  getContainerStats(id) {
    return this.request(`/api/containers/${id}/stats`);
  }

  // Process Isolation & Namespaces
  getContainerProcesses(id) {
    return this.request(`/api/containers/${id}/processes`);
  }

  getNamespaceArchitecture() {
    return this.request("/api/processes/architecture");
  }

  compareProcesses(containerIds) {
    return this.request("/api/processes/compare", {
      method: "POST",
      body: JSON.stringify({ container_ids: containerIds }),
    });
  }

  // Resource Management
  getContainerResources(id) {
    return this.request(`/api/containers/${id}/resources`);
  }

  updateContainerResources(id, cpuLimit, memLimit) {
    return this.request(`/api/containers/${id}/resources`, {
      method: "POST",
      body: JSON.stringify({
        cpu_limit: cpuLimit !== undefined ? parseFloat(cpuLimit) : undefined,
        memory_limit_mb: memLimit !== undefined ? parseInt(memLimit, 10) : undefined,
      }),
    });
  }

  // Live Telemetry & Monitoring
  getMonitoringOverview() {
    return this.request("/api/monitoring/overview");
  }

  getMonitoringHistory(containerId = null, minutes = 30) {
    const query = containerId ? `container_id=${containerId}&minutes=${minutes}` : `minutes=${minutes}`;
    return this.request(`/api/monitoring/history?${query}`);
  }

  // Analytics
  getAnalyticsOverview(timeframe = 60) {
    return this.request(`/api/analytics/overview?timeframe=${timeframe}`);
  }

  // Activity Audit Log
  getActivityLogs(params = {}) {
    const q = new URLSearchParams();
    if (params.limit) q.append("limit", params.limit);
    if (params.event_type) q.append("event_type", params.event_type);
    if (params.container_id) q.append("container_id", params.container_id);
    if (params.search) q.append("search", params.search);
    return this.request(`/api/activity?${q.toString()}`);
  }
}

window.api = new NexoraAPI();
