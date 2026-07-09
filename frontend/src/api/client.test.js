import { afterEach, describe, expect, it, vi } from "vitest";

import { api, ApiError } from "./client";

function mockFetchOnce(body, { ok = true, status = 200 } = {}) {
  global.fetch = vi.fn().mockResolvedValue({
    ok,
    status,
    json: async () => body,
  });
}

afterEach(() => {
  vi.restoreAllMocks();
});

describe("api.request (via getDashboard)", () => {
  it("returns the parsed JSON body on success", async () => {
    mockFetchOnce({ portfolio: { equity: 100 } });

    const result = await api.getDashboard();

    expect(result).toEqual({ portfolio: { equity: 100 } });
  });

  it("throws an ApiError with status 0 when the network request fails", async () => {
    global.fetch = vi.fn().mockRejectedValue(new TypeError("network down"));

    await expect(api.getDashboard()).rejects.toMatchObject({
      name: "ApiError",
      status: 0,
    });
  });

  it("throws an ApiError using the response's detail field on a non-ok response", async () => {
    mockFetchOnce(
      { detail: "Cannot switch modes while a position is open." },
      { ok: false, status: 409 },
    );

    await expect(api.getDashboard()).rejects.toMatchObject({
      name: "ApiError",
      status: 409,
      message: "Cannot switch modes while a position is open.",
    });
  });

  it("falls back to a generic message when the error response has no JSON body", async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 500,
      json: async () => {
        throw new Error("not json");
      },
    });

    await expect(api.getDashboard()).rejects.toMatchObject({
      status: 500,
      message: "Request failed (500)",
    });
  });

  it("returns null for a 204 No Content response", async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 204,
      json: async () => {
        throw new Error("should not be called");
      },
    });

    const result = await api.getDashboard();

    expect(result).toBeNull();
  });
});

describe("api request construction", () => {
  it("sends PUT with a JSON body for updateSettings", async () => {
    mockFetchOnce({ mode: "paper" });

    await api.updateSettings({ mode: "live" });

    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining("/settings"),
      expect.objectContaining({
        method: "PUT",
        body: JSON.stringify({ mode: "live" }),
      }),
    );
  });

  it("sends POST for runner control endpoints", async () => {
    mockFetchOnce({ started: true });

    await api.startRunner();

    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining("/runner/start"),
      expect.objectContaining({ method: "POST" }),
    );
  });

  it("builds the job history query string with page and jtype", async () => {
    mockFetchOnce({ items: [] });

    await api.getJobHistory(2, "optimizer");

    const [url] = global.fetch.mock.calls[0];

    expect(url).toContain("/jobs/history?");
    expect(url).toContain("page=2");
    expect(url).toContain("jtype=optimizer");
  });

  it("omits jtype from the query string when jobType is 'all'", async () => {
    mockFetchOnce({ items: [] });

    await api.getJobHistory(1, "all");

    const [url] = global.fetch.mock.calls[0];

    expect(url).not.toContain("jtype");
  });

  it("resetJob POSTs to /jobs/reset", async () => {
    mockFetchOnce({ reset: true });

    await api.resetJob();

    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining("/jobs/reset"),
      expect.objectContaining({ method: "POST" }),
    );
  });

  it("getLiveBalance GETs /account/live-balance", async () => {
    mockFetchOnce({ balance: 123.45, source: "binance_testnet" });

    await api.getLiveBalance();

    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining("/account/live-balance"),
      expect.any(Object),
    );
  });
});

describe("ApiError", () => {
  it("carries the HTTP status on the error instance", () => {
    const error = new ApiError("boom", 404);

    expect(error).toBeInstanceOf(Error);
    expect(error.name).toBe("ApiError");
    expect(error.status).toBe(404);
    expect(error.message).toBe("boom");
  });
});
