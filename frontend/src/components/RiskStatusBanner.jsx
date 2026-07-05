import { formatUsd, formatPercent } from "../lib/format";

const HALT_REASON_LABELS = {
  DAILY_LOSS_LIMIT_REACHED: "Daily loss limit reached",
  DAILY_TRADE_LIMIT_REACHED: "Daily trade limit reached",
};

export function RiskStatusBanner({ riskStatus }) {
  if (!riskStatus) return null;

  if (!riskStatus.trading_halted) {
    return (
      <div className="risk-banner risk-banner--ok">
        <span className="risk-banner__dot" />
        <span className="risk-banner__text">
          Daily limits clear — {riskStatus.daily_trade_count}/
          {riskStatus.max_daily_trades} trades today
          {riskStatus.daily_pnl < 0 && (
            <>
              {" "}· {formatPercent(riskStatus.daily_loss_percent)} of{" "}
              {formatPercent(riskStatus.max_daily_loss_percent)} daily loss
              budget used
            </>
          )}
        </span>
      </div>
    );
  }

  const reasonLabel =
    HALT_REASON_LABELS[riskStatus.halt_reason] || riskStatus.halt_reason;

  return (
    <div className="risk-banner risk-banner--halted">
      <span className="risk-banner__dot" />
      <span className="risk-banner__text">
        <strong>Trading paused for today — {reasonLabel}.</strong> No new
        positions will open until the next UTC day.{" "}
        {riskStatus.halt_reason === "DAILY_LOSS_LIMIT_REACHED" && (
          <>
            Today's PnL: {formatUsd(riskStatus.daily_pnl, { signed: true })} (
            {formatPercent(riskStatus.daily_loss_percent)} of{" "}
            {formatPercent(riskStatus.max_daily_loss_percent)} limit)
          </>
        )}
        {riskStatus.halt_reason === "DAILY_TRADE_LIMIT_REACHED" && (
          <>
            {riskStatus.daily_trade_count}/{riskStatus.max_daily_trades}{" "}
            trades today
          </>
        )}
      </span>
    </div>
  );
}
