import {
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { Operation } from "./Operation";
import { api, ApiError } from "../api/client";

vi.mock("../api/client", async () => {
  const actual = await vi.importActual("../api/client");
  return {
    ...actual,
    api: {
      getSettings: vi.fn(),
      updateSettings: vi.fn(),
      getLiveBalance: vi.fn(),
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
};

beforeEach(() => {
  vi.clearAllMocks();
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe("Operation", () => {
  it("shows a loading state before settings resolve", () => {
    api.getSettings.mockReturnValue(new Promise(() => {}));

    render(<Operation />);

    expect(screen.getByText(/carregando configurações/i)).toBeInTheDocument();
  });

  it("shows an error state when the API is unreachable", async () => {
    api.getSettings.mockRejectedValue(
      new ApiError("Could not reach the API. Is it running?", 0),
    );

    render(<Operation />);

    await waitFor(() =>
      expect(
        screen.getByText("Não foi possível conectar à API"),
      ).toBeInTheDocument(),
    );
  });

  it("renders the mode and credentials panels once settings load", async () => {
    api.getSettings.mockResolvedValue(SETTINGS_FIXTURE);

    render(<Operation />);

    await waitFor(() =>
      expect(screen.getByText("Modo de execução")).toBeInTheDocument(),
    );

    expect(screen.getByText("Credenciais da carteira")).toBeInTheDocument();

    // paper mode is active by default in the fixture
    expect(screen.getAllByText("Ativo").length).toBeGreaterThanOrEqual(1);
  });

  it("locks Live mode options until live trading is confirmed", async () => {
    api.getSettings.mockResolvedValue(SETTINGS_FIXTURE);

    render(<Operation />);

    await waitFor(() =>
      expect(screen.getByText("Modo de execução")).toBeInTheDocument(),
    );

    expect(
      screen.getByText((_, element) =>
        element?.tagName.toLowerCase() === "p" &&
        element.textContent.includes(
          "Para habilitar os modos Live, vá em Credenciais",
        ),
      ),
    ).toBeInTheDocument();

    const liveTestnetButton = screen
      .getByText("Live Testnet")
      .closest("button");

    expect(liveTestnetButton).toBeDisabled();
  });

  it("opens a confirmation modal when switching to an available mode", async () => {
    const user = userEvent.setup();

    api.getSettings.mockResolvedValue({
      ...SETTINGS_FIXTURE,
      live_trading_available: true,
    });
    api.updateSettings.mockResolvedValue({
      ...SETTINGS_FIXTURE,
      mode: "live",
      binance_testnet: true,
      restart_triggered: true,
    });

    render(<Operation />);

    await waitFor(() =>
      expect(screen.getByText("Modo de execução")).toBeInTheDocument(),
    );

    await user.click(screen.getByText("Live Testnet").closest("button"));

    expect(screen.getByText("Trocar para Live Testnet?")).toBeInTheDocument();

    await user.click(
      screen.getByRole("button", { name: "Trocar para Live Testnet" }),
    );

    await waitFor(() =>
      expect(api.updateSettings).toHaveBeenCalledWith({
        mode: "live",
        binance_testnet: true,
      }),
    );
  });

  it("hides the credentials save bar until a field is dirty, mirroring the Settings page pattern", async () => {
    const user = userEvent.setup();

    api.getSettings.mockResolvedValue(SETTINGS_FIXTURE);
    api.updateSettings.mockResolvedValue({
      ...SETTINGS_FIXTURE,
      restart_triggered: false,
    });

    render(<Operation />);

    await waitFor(() =>
      expect(screen.getByText("Credenciais da carteira")).toBeInTheDocument(),
    );

    const saveBar = document.querySelector(".params-save-bar");
    expect(saveBar).not.toHaveClass("params-save-bar--visible");

    const apiKeyInput = screen.getAllByPlaceholderText(
      "Cole a chave de 64 caracteres",
    )[0];

    fireEvent.change(apiKeyInput, { target: { value: "a".repeat(64) } });

    expect(saveBar).toHaveClass("params-save-bar--visible");

    const saveButton = within(saveBar).getByRole("button", {
      name: /salvar alterações/i,
    });

    expect(saveButton).toBeEnabled();

    await user.click(saveButton);

    await waitFor(() =>
      expect(api.updateSettings).toHaveBeenCalledWith(
        expect.objectContaining({ binance_api_key: "a".repeat(64) }),
      ),
    );
  });
});
