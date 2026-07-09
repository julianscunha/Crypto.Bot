import { render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { Dashboard } from "./Dashboard";
import { api, ApiError } from "../api/client";

vi.mock("../api/client", async () => {
  const actual = await vi.importActual("../api/client");
  return {
    ...actual,
    api: {
      getDashboard: vi.fn(),
      getRiskStatus: vi.fn(),
      getAdvancedMetrics: vi.fn(),
    },
  };
});

const DASHBOARD_FIXTURE = {
  runtime: {
    websocket_connected: true,
    uptime_seconds: 3725,
    active_symbols: ["BTCUSDT", "ETHUSDT"],
    blocked_signal_reasons: {},
    execution_reasons: {},
  },
  metrics: {
    winrate: 55.5,
    winning_trades: 5,
    losing_trades: 4,
    expectancy: 12.34,
    total_trades: 9,
  },
  portfolio: {
    equity: 1234.56,
    balance: 1000,
    total_pnl: 234.56,
    realized_pnl: 200,
    drawdown: 2.5,
    exposure: 300,
    open_positions: 1,
  },
  open_trades: [],
  recent_closed_trades: [],
};

const RISK_STATUS_FIXTURE = {
  trading_halted: false,
  daily_trade_count: 2,
  max_daily_trades: 20,
  daily_pnl: 10,
  daily_loss_percent: 0,
  max_daily_loss_percent: 5,
};

afterEach(() => {
  vi.restoreAllMocks();
});

describe("Dashboard", () => {
  it("shows a loading state before the first fetch resolves", () => {
    api.getDashboard.mockReturnValue(new Promise(() => {}));
    api.getRiskStatus.mockReturnValue(new Promise(() => {}));
    api.getAdvancedMetrics.mockReturnValue(new Promise(() => {}));

    render(<Dashboard />);

    expect(screen.getByText(/connecting to the engine/i)).toBeInTheDocument();
  });

  it("renders portfolio data once the dashboard fetch resolves", async () => {
    api.getDashboard.mockResolvedValue(DASHBOARD_FIXTURE);
    api.getRiskStatus.mockResolvedValue(RISK_STATUS_FIXTURE);
    api.getAdvancedMetrics.mockResolvedValue({ sample_size: 0 });

    render(<Dashboard />);

    await waitFor(() =>
      expect(screen.getByText("Trading Session")).toBeInTheDocument(),
    );

    expect(screen.getByText("$1,234.56")).toBeInTheDocument();
    expect(screen.getByText("Market feed live")).toBeInTheDocument();
    expect(
      screen.getByText("No open positions. The bot is watching the market."),
    ).toBeInTheDocument();
  });

  it("shows an error state when the API is unreachable", async () => {
    api.getDashboard.mockRejectedValue(
      new ApiError("Could not reach the API. Is it running?", 0),
    );
    api.getRiskStatus.mockRejectedValue(new ApiError("down", 0));
    api.getAdvancedMetrics.mockRejectedValue(new ApiError("down", 0));

    render(<Dashboard />);

    await waitFor(() =>
      expect(screen.getByText("Can't reach the API")).toBeInTheDocument(),
    );

    expect(
      screen.getByText("Could not reach the API. Is it running?"),
    ).toBeInTheDocument();
  });

  it("shows the feed-down badge when the websocket is disconnected", async () => {
    api.getDashboard.mockResolvedValue({
      ...DASHBOARD_FIXTURE,
      runtime: {
        ...DASHBOARD_FIXTURE.runtime,
        websocket_connected: false,
      },
    });
    api.getRiskStatus.mockResolvedValue(RISK_STATUS_FIXTURE);
    api.getAdvancedMetrics.mockResolvedValue({ sample_size: 0 });

    render(<Dashboard />);

    await waitFor(() =>
      expect(screen.getByText("Feed down")).toBeInTheDocument(),
    );
  });
});
