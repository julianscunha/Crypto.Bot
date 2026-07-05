import { Badge } from "./Badge";
import {
  formatUsd,
  formatPrice,
  formatQuantity,
  formatDateTime,
  toneForValue,
} from "../lib/format";

export function TradesTable({ trades, variant }) {
  if (!trades || trades.length === 0) {
    return (
      <div className="empty-state">
        {variant === "open"
          ? "No open positions. The bot is watching the market."
          : "No closed trades yet."}
      </div>
    );
  }

  return (
    <div className="table-scroll">
      <table className="table">
        <thead>
          <tr>
            <th>Symbol</th>
            <th>Side</th>
            <th>Entry</th>
            <th>{variant === "open" ? "Current" : "Exit"}</th>
            <th>Qty</th>
            <th>PnL</th>
            {variant === "open" && <th>Stop / Target</th>}
            {variant === "closed" && <th>Reason</th>}
            <th>{variant === "open" ? "Opened" : "Closed"}</th>
          </tr>
        </thead>
        <tbody>
          {trades.map((trade) => {
            const pnlValue =
              variant === "open" ? trade.unrealized_pnl : trade.pnl;

            return (
              <tr key={trade.id}>
                <td className="table__symbol">{trade.symbol}</td>
                <td>
                  <Badge tone={trade.action === "BUY" ? "positive" : "negative"}>
                    {trade.action}
                  </Badge>
                </td>
                <td className="mono">{formatPrice(trade.entry_price)}</td>
                <td className="mono">
                  {formatPrice(
                    variant === "open"
                      ? trade.current_price
                      : trade.current_price,
                  )}
                </td>
                <td className="mono">{formatQuantity(trade.quantity)}</td>
                <td className={`mono tone-${toneForValue(pnlValue)}`}>
                  {formatUsd(pnlValue, { signed: true })}
                </td>
                {variant === "open" && (
                  <td className="mono table__substack">
                    <span className="tone-negative">
                      {formatPrice(trade.stop_loss)}
                    </span>
                    <span className="tone-positive">
                      {formatPrice(trade.take_profit)}
                    </span>
                  </td>
                )}
                {variant === "closed" && (
                  <td>
                    <span className="table__reason">
                      {trade.exit_reason || "—"}
                    </span>
                  </td>
                )}
                <td className="table__time">
                  {formatDateTime(
                    variant === "open" ? trade.created_at : trade.closed_at,
                  )}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
