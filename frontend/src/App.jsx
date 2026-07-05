import { useState, useEffect, useCallback } from "react";
import { usePolling } from "./hooks/usePolling";
import { api, ApiError } from "./api/client";
import { Dashboard } from "./pages/Dashboard";
import { Settings } from "./pages/Settings";
import { Tools } from "./pages/Tools";
import "./App.css";
import "./components.css";

const NAV_ITEMS = [
  { id: "dashboard", label: "Monitor" },
  { id: "tools", label: "Ferramentas" },
  { id: "settings", label: "Configurações" },
];

const MODE_LABELS = {
  paper: "PAPER",
  live_testnet: "LIVE TESTNET",
  live_mainnet: "LIVE MAINNET",
};

function getModeKey(health) {
  if (!health) return null;
  if (health.mode !== "live") return "paper";
  return health.testnet ? "live_testnet" : "live_mainnet";
}

export default function App() {
  const [activePage, setActivePage] = useState("dashboard");
  const { data: health } = usePolling(api.getHealth, 5000);
  const { data: runnerStatus, refresh: refreshRunner } = usePolling(api.getRunnerStatus, 3000);

  const [ping, setPing] = useState(null);
  const [isTogglingRunner, setIsTogglingRunner] = useState(false);
  const [runnerError, setRunnerError] = useState(null);
  const [jobStatus, setJobStatus] = useState(null);

  useEffect(() => {
    async function pollJob() {
      try { setJobStatus((await api.getJobStatus()).status); } catch {}
    }
    pollJob();
    const i = setInterval(pollJob, 5000);
    return () => clearInterval(i);
  }, []);

  const jobRunning = jobStatus === "running";

  // Mede ping a cada 10s
  useEffect(() => {
    async function measure() {
      try {
        const ms = await api.getPing();
        setPing(ms);
      } catch {
        setPing(null);
      }
    }
    measure();
    const interval = setInterval(measure, 10000);
    return () => clearInterval(interval);
  }, []);

  const isConnected = health != null;
  const isRunning = runnerStatus?.running ?? false;
  const mode = health?.mode ?? null;
  const modeKey = getModeKey(health);

  const modeColor = modeKey === "live_mainnet"
    ? "var(--signal-negative)"
    : modeKey === "live_testnet"
    ? "var(--signal-positive)"
    : "var(--text-muted)";

  async function handleToggleRunner() {
    setIsTogglingRunner(true);
    setRunnerError(null);
    try {
      if (isRunning) {
        await api.stopRunner();
      } else {
        if (jobRunning) {
          setRunnerError("Aguarde o optimizer/backtest terminar antes de iniciar o bot.");
          return;
        }
        await api.startRunner();
      }
      setTimeout(() => refreshRunner(), 1500);
    } catch (err) {
      setRunnerError(err instanceof ApiError ? err.message : "Falha ao alterar estado do bot.");
    } finally {
      setIsTogglingRunner(false);
    }
  }

  const pingColor = ping == null
    ? "var(--text-muted)"
    : ping < 100 ? "var(--signal-positive)"
    : ping < 300 ? "#f0b429"
    : "var(--signal-negative)";



  return (
    <div className="shell">
      <aside className="shell__sidebar">
        <div className="brand">
          <span className="brand__mark">CB</span>
          <div className="brand__text">
            <span className="brand__name">CRYPTO.BOT</span>
            <span className="brand__sub">terminal</span>
          </div>
        </div>

        <nav className="nav">
          {NAV_ITEMS.map((item) => (
            <button
              key={item.id}
              className={`nav__item ${activePage === item.id ? "nav__item--active" : ""}`}
              onClick={() => setActivePage(item.id)}
            >
              {item.label}
            </button>
          ))}
        </nav>

        <div className="shell__bottom">
          {/* Play/Stop */}
          <button
            className={`runner-toggle ${isRunning ? "runner-toggle--stop" : "runner-toggle--start"}`}
            onClick={handleToggleRunner}
            disabled={isTogglingRunner || !isConnected || (!isRunning && jobRunning)}
            title={
              jobRunning && !isRunning
                ? "Aguarde o optimizer/backtest terminar"
                : isRunning ? "Parar o bot" : "Iniciar o bot"
            }
          >
            {isTogglingRunner
              ? "Aguarde…"
              : isRunning
              ? "⏹ Parar bot"
              : "▶ Iniciar bot"}
          </button>

          {runnerError && (
            <div className="runner-error">{runnerError}</div>
          )}

          {/* Status badge */}
          <div className="shell__status">
            <span className={`status-dot ${isConnected ? "status-dot--ok" : "status-dot--off"}`} />
            <div className="shell__status-text">
              <span className="shell__status-label">
                {isConnected ? "API conectada" : "API offline"}
              </span>
              <div className="shell__status-meta">
                {mode && (
                  <span className="shell__mode" style={{ color: modeColor }}>
                    {MODE_LABELS[modeKey] ?? mode?.toUpperCase()}
                  </span>
                )}
                {ping != null && (
                  <span className="shell__ping" style={{ color: pingColor }}>
                    {ping}ms
                  </span>
                )}
              </div>
            </div>
          </div>
        </div>
      </aside>

      <main className="shell__main">
        {activePage === "dashboard" && <Dashboard />}
        {activePage === "tools" && <Tools />}
        {activePage === "settings" && <Settings />}
      </main>
    </div>
  );
}
