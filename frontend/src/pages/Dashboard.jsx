import { usePolling } from "../hooks/usePolling";
import { api, ApiError } from "../api/client";
import { Panel } from "../components/Panel";
import { StatCard } from "../components/StatCard";
import { Badge } from "../components/Badge";
import { TradesTable } from "../components/TradesTable";
import { PnlChart } from "../components/PnlChart";
import { EventLog } from "../components/EventLog";
import { RiskStatusBanner } from "../components/RiskStatusBanner";
import { AdvancedMetricsPanel } from "../components/AdvancedMetricsPanel";
import {
  formatUsd,
  formatPercent,
  formatUptime,
  toneForValue,
} from "../lib/format";

export function Dashboard() {
  const { data, error, isLoading } = usePolling(api.getDashboard, 3000);
  const { data: riskStatus } = usePolling(api.getRiskStatus, 5000);
  const { data: advancedMetrics } = usePolling(api.getAdvancedMetrics, 5000);

  if (isLoading && !data) {
    return <div className="loading-state">Connecting to the engine…</div>;
  }

  if (error && !data) {
    return (
      <div className="error-state">
        <h2>Can't reach the API</h2>
        <p>
          {error instanceof ApiError
            ? error.message
            : "An unexpected error occurred."}
        </p>
        <p className="error-state__hint">
          Start it with <code>uvicorn apps.api.main:app</code> or run the
          launcher's Full Stack option.
        </p>
      </div>
    );
  }

  const { runtime, metrics, portfolio, open_trades, recent_closed_trades } =
    data;

  return (
    <div className="dashboard">
      <header className="dashboard__header">
        <div>
          <span className="dashboard__eyebrow">Live monitor</span>
          <h1 className="dashboard__title">Trading Session</h1>
        </div>
        <div className="dashboard__header-meta">
          <Badge tone={runtime.websocket_connected ? "positive" : "negative"}>
            {runtime.websocket_connected ? "Market feed live" : "Feed down"}
          </Badge>
          <span className="mono dashboard__uptime">
            uptime {formatUptime(runtime.uptime_seconds)}
          </span>
        </div>
      </header>

      <RiskStatusBanner riskStatus={riskStatus} />

      <section className="stat-grid">
        <StatCard
          label="Equity"
          value={formatUsd(portfolio.equity)}
          sublabel={`Balance ${formatUsd(portfolio.balance)}`}
        />
        <StatCard
          label="Total PnL"
          value={formatUsd(portfolio.total_pnl, { signed: true })}
          tone={toneForValue(portfolio.total_pnl)}
          sublabel={`Realized ${formatUsd(portfolio.realized_pnl, {
            signed: true,
          })}`}
        />
        <StatCard
          label="Drawdown"
          value={formatPercent(portfolio.drawdown)}
          tone={portfolio.drawdown > 0 ? "warning" : "neutral"}
          sublabel={`Exposure ${formatUsd(portfolio.exposure)}`}
        />
        <StatCard
          label="Win rate"
          value={formatPercent(metrics.winrate, { decimals: 1 })}
          sublabel={`${metrics.winning_trades}W / ${metrics.losing_trades}L`}
        />
        <StatCard
          label="Open positions"
          value={portfolio.open_positions}
          sublabel={`${active(runtime.active_symbols)}`}
        />
        <StatCard
          label="Expectancy"
          value={formatUsd(metrics.expectancy, { signed: true })}
          tone={toneForValue(metrics.expectancy)}
          sublabel={`${metrics.total_trades} trades total`}
        />
      </section>

      <section className="dashboard__grid">
        <Panel
          eyebrow="Positions"
          title="Open trades"
          className="dashboard__span-2"
        >
          <TradesTable trades={open_trades} variant="open" />
        </Panel>

        <Panel eyebrow="Pipeline" title="Signal activity">
          <EventLog runtime={runtime} />
        </Panel>

        <Panel
          eyebrow="History"
          title="Recent closed trades"
          className="dashboard__span-2"
        >
          <TradesTable trades={recent_closed_trades} variant="closed" />
        </Panel>

        <Panel eyebrow="Performance" title="PnL by trade">
          <PnlChart trades={recent_closed_trades} />
        </Panel>

        <Panel
          eyebrow="Strategy quality"
          title="Risk-adjusted performance"
          className="dashboard__span-3"
        >
          <AdvancedMetricsPanel metrics={advancedMetrics} />
        </Panel>
      </section>
    </div>
  );
}

function active(symbols) {
  if (!symbols || symbols.length === 0) return "No active symbols";
  return symbols.join(" · ");
}
