const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";

class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

async function request(path, options = {}) {
  let response;

  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      headers: {
        "Content-Type": "application/json",
        ...options.headers,
      },
      ...options,
    });
  } catch (_networkError) {
    throw new ApiError(
      "Could not reach the API. Is it running?",
      0,
    );
  }

  if (!response.ok) {
    let detail = `Request failed (${response.status})`;

    try {
      const body = await response.json();
      detail = body.detail || detail;
    } catch {
      // response had no JSON body; keep the generic message
    }

    throw new ApiError(detail, response.status);
  }

  if (response.status === 204) {
    return null;
  }

  return response.json();
}

export const api = {
  getDashboard: () => request("/dashboard"),
  getRuntime: () => request("/runtime"),
  getPortfolio: () => request("/portfolio"),
  getMetrics: () => request("/metrics"),
  getAdvancedMetrics: () => request("/metrics/advanced"),
  getRiskStatus: () => request("/risk-status"),
  getOpenTrades: () => request("/trades/open"),
  getClosedTrades: () => request("/trades/closed"),
  getHealth: () => request("/health"),
  getSettings: () => request("/settings"),
  updateSettings: (payload) =>
    request("/settings", {
      method: "PUT",
      body: JSON.stringify(payload),
    }),
  getRunnerStatus: () => request("/runner/status"),
  stopRunner: () => request("/runner/stop", { method: "POST" }),
  startRunner: () => request("/runner/start", { method: "POST" }),
  getLiveBalance: () => request("/account/live-balance"),
  getJobProgress: () => request("/jobs/progress"),
  getJobHistory: (page = 1) => request(`/jobs/history?page=${page}`),
  getJobEstimate: (job_type, days) => request(`/jobs/estimate?jtype=${job_type}&days=${days ?? ""}`),
  previewApply: () => request("/jobs/preview-apply"),
  resetJob: () => request("/jobs/reset", { method: "POST" }),
  runOptimizer: (days = 90) => request(`/jobs/optimizer?days=${days}`, { method: "POST" }),
  runBacktest: () => request("/jobs/backtest", { method: "POST" }),
  applyBestConfig: () => request("/jobs/apply", { method: "POST" }),

  // Mede o round-trip real em ms comparando timestamp local com o do servidor
  async getPing() {
    const sent = Date.now();
    await request("/health");
    const received = Date.now();
    return received - sent;
  },
};

export { ApiError, API_BASE_URL };
