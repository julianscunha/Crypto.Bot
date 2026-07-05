import { StatCard } from "./StatCard";
import { formatUsd } from "../lib/format";

function toneForRatio(value) {
  if (value == null) return "neutral";
  if (value > 0) return "positive";
  if (value < 0) return "negative";
  return "neutral";
}

export function AdvancedMetricsPanel({ metrics }) {
  if (!metrics || metrics.sample_size === 0) {
    return (
      <div className="empty-state">
        Not enough closed trades yet to compute risk-adjusted metrics.
      </div>
    );
  }

  return (
    <div className="advanced-metrics-grid">
      <StatCard
        label="Sharpe ratio"
        value={metrics.sharpe_ratio.toFixed(2)}
        tone={toneForRatio(metrics.sharpe_ratio)}
        sublabel="Return per unit of volatility"
      />
      <StatCard
        label="Sortino ratio"
        value={metrics.sortino_ratio.toFixed(2)}
        tone={toneForRatio(metrics.sortino_ratio)}
        sublabel="Return per unit of downside risk"
      />
      <StatCard
        label="Max drawdown"
        value={formatUsd(metrics.max_drawdown)}
        tone={metrics.max_drawdown < 0 ? "negative" : "neutral"}
        sublabel="Peak-to-trough, all-time"
      />
      <StatCard
        label="Profit factor"
        value={metrics.profit_factor.toFixed(2)}
        tone={metrics.profit_factor >= 1 ? "positive" : "negative"}
        sublabel="Gross profit ÷ gross loss"
      />
      <StatCard
        label="Win streak"
        value={`${metrics.current_win_streak}`}
        sublabel={`Best: ${metrics.max_win_streak}`}
        tone={metrics.current_win_streak > 0 ? "positive" : "neutral"}
      />
      <StatCard
        label="Loss streak"
        value={`${metrics.current_loss_streak}`}
        sublabel={`Worst: ${metrics.max_loss_streak}`}
        tone={metrics.current_loss_streak > 0 ? "negative" : "neutral"}
      />
    </div>
  );
}
