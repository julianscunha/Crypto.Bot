import {
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { Settings } from "./Settings";
import { api, ApiError } from "../api/client";

vi.mock("../api/client", async () => {
  const actual = await vi.importActual("../api/client");
  return {
    ...actual,
    api: {
      getSettings: vi.fn(),
      updateSettings: vi.fn(),
    },
  };
});

const SETTINGS_FIXTURE = {
  mode: "paper",
  binance_testnet: true,
  live_trading_confirmed: false,
  live_trading_available: false,
  account_balance: 100,
  binance_api_key_set: false,
  binance_api_key_masked: null,
  binance_secret_key_set: false,
  binance_secret_key_masked: null,
  symbols: "BTCUSDT,ETHUSDT",
  kline_interval: "5m",

  risk_per_trade_percent: 1,
  max_open_positions: 3,
  max_position_exposure_percent: 25,
  minimum_risk_reward_ratio: 1.2,

  enable_daily_trade_limit: true,
  max_daily_trades: 20,
  enable_daily_loss_limit: true,
  max_daily_loss_percent: 5,
  enable_drawdown_protection: true,
  maximum_daily_drawdown_percent: 5,

  atr_period: 14,
  atr_stop_multiplier: 1,
  atr_take_profit_multiplier: 2,
  atr_trailing_multiplier: 1,
  minimum_atr_percent: 0.01,

  minimum_signal_strength: 0.5,
  min_signal_confidence: 0.45,
  enable_volatility_filter: true,
  enable_ema_trend_filter: true,
  enable_market_regime_alignment: false,
  enable_signal_cooldown: true,
  signal_cooldown_seconds: 5,

  structure_min_score: 2,
  structure_min_impulse_percent: 0.1,
  structure_enable_consolidation_filter: true,

  enable_trailing_stop: true,
  enable_breakeven: true,
  breakeven_trigger_percent: 0.5,
  enable_dynamic_take_profit: false,
  dynamic_take_profit_proximity_percent: 90,

  quantity_precision: 5,
  price_precision: 2,
  min_order_quantity: 0.0001,
  min_order_notional: 10,

  enable_fee_simulation: true,
  maker_fee_percent: 0.001,
  enable_slippage_simulation: true,
  taker_fee_percent: 0.001,
};

beforeEach(() => {
  vi.clearAllMocks();

  // PairsPanel fetches Binance's public exchangeInfo directly in the
  // browser -- there's no network access in this test environment,
  // so make it fail fast and fall back to its DEFAULT_PAIRS list.
  global.fetch = vi.fn().mockRejectedValue(new Error("no network in tests"));
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe("Settings", () => {
  it("shows a loading state before settings resolve", () => {
    api.getSettings.mockReturnValue(new Promise(() => {}));

    render(<Settings />);

    expect(screen.getByText(/carregando configurações/i)).toBeInTheDocument();
  });

  it("shows an error state when the API is unreachable", async () => {
    api.getSettings.mockRejectedValue(
      new ApiError("Could not reach the API. Is it running?", 0),
    );

    render(<Settings />);

    await waitFor(() =>
      expect(
        screen.getByText("Não foi possível conectar à API"),
      ).toBeInTheDocument(),
    );
  });

  it("renders the parameter panels once settings load", async () => {
    api.getSettings.mockResolvedValue(SETTINGS_FIXTURE);

    render(<Settings />);

    await waitFor(() =>
      expect(
        screen.getByText("Pares monitorados e mercado"),
      ).toBeInTheDocument(),
    );

    expect(screen.getByText("Gestão de risco")).toBeInTheDocument();

    // Mode/credentials panels moved to the Operação page -- Settings
    // no longer renders them.
    expect(screen.queryByText("Modo de execução")).not.toBeInTheDocument();
    expect(
      screen.queryByText("Credenciais da carteira"),
    ).not.toBeInTheDocument();
  });

  it("marks a parameter field dirty and saves parsed values", async () => {
    const user = userEvent.setup();

    api.getSettings.mockResolvedValue(SETTINGS_FIXTURE);
    api.updateSettings.mockResolvedValue({
      ...SETTINGS_FIXTURE,
      restart_triggered: false,
    });

    render(<Settings />);

    await waitFor(() =>
      expect(screen.getByText("Gestão de risco")).toBeInTheDocument(),
    );

    const riskInput = screen.getByLabelText(/Risco por trade/i);

    // fireEvent.change instead of user.clear/type -- a controlled
    // number input re-typed keystroke by keystroke can pass through
    // transient values number inputs don't like (e.g. an empty
    // string mid-edit), which is an unrelated source of flakiness
    // this test doesn't care about.
    fireEvent.change(riskInput, { target: { value: "2.5" } });

    const saveBar = document.querySelector(".params-save-bar");

    const saveButton = within(saveBar).getByRole("button", {
      name: /salvar alterações/i,
    });

    expect(saveButton).toBeEnabled();

    await user.click(saveButton);

    await waitFor(() => expect(api.updateSettings).toHaveBeenCalled());

    const payload = api.updateSettings.mock.calls.at(-1)[0];

    expect(payload.risk_per_trade_percent).toBeCloseTo(2.5);

    await waitFor(() =>
      expect(
        within(saveBar).getByText(/reinicie o bot para aplicar/i),
      ).toBeInTheDocument(),
    );
  });

  it("uses a single save bar for pairs, market fields and parameters together", async () => {
    const user = userEvent.setup();

    api.getSettings.mockResolvedValue(SETTINGS_FIXTURE);
    api.updateSettings.mockResolvedValue({
      ...SETTINGS_FIXTURE,
      restart_triggered: false,
    });

    render(<Settings />);

    await waitFor(() =>
      expect(
        screen.getByText("Pares monitorados e mercado"),
      ).toBeInTheDocument(),
    );

    // only one sticky save bar on the whole page -- pairs/market
    // fields no longer have their own separate save button
    expect(
      document.querySelectorAll(".params-save-bar"),
    ).toHaveLength(1);

    await waitFor(() =>
      expect(screen.getByText("BNB")).toBeInTheDocument(),
    );

    // BNBUSDT isn't in SETTINGS_FIXTURE.symbols -- toggling it adds
    // a pair rather than removing one already selected
    await user.click(screen.getByText("BNB").closest("button"));

    const saveBar = document.querySelector(".params-save-bar");

    const saveButton = within(saveBar).getByRole("button", {
      name: /salvar alterações/i,
    });

    expect(saveButton).toBeEnabled();

    expect(
      within(saveBar).getByText(/requer reinicialização do bot/i),
    ).toBeInTheDocument();

    await user.click(saveButton);

    await waitFor(() =>
      expect(api.updateSettings).toHaveBeenCalledWith(
        expect.objectContaining({
          symbols: expect.stringContaining("BNB"),
        }),
      ),
    );
  });
});
