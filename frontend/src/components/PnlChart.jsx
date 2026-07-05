import {
  ResponsiveContainer,
  BarChart,
  Bar,
  Cell,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  ReferenceLine,
} from "recharts";
import { formatUsd } from "../lib/format";

function CustomTooltip({ active, payload }) {
  if (!active || !payload || !payload.length) return null;
  const point = payload[0].payload;
  return (
    <div className="chart-tooltip">
      <span className="chart-tooltip__symbol">{point.symbol}</span>
      <span
        className={`mono chart-tooltip__pnl ${
          point.pnl >= 0 ? "tone-positive" : "tone-negative"
        }`}
      >
        {formatUsd(point.pnl, { signed: true })}
      </span>
    </div>
  );
}

export function PnlChart({ trades }) {
  if (!trades || trades.length === 0) {
    return <div className="empty-state">No closed trades to chart yet.</div>;
  }

  const data = trades.map((trade, index) => ({
    index: index + 1,
    symbol: trade.symbol,
    pnl: trade.pnl,
  }));

  const maxAbs = Math.max(...data.map((d) => Math.abs(d.pnl)), 0.0001);
  const domainPadding = maxAbs * 1.3;

  return (
    <ResponsiveContainer width="100%" height={180}>
      <BarChart data={data} margin={{ top: 8, right: 8, left: 8, bottom: 0 }}>
        <CartesianGrid stroke="#232b38" vertical={false} />
        <XAxis
          dataKey="index"
          tick={{ fill: "#566073", fontSize: 11, fontFamily: "JetBrains Mono" }}
          axisLine={{ stroke: "#232b38" }}
          tickLine={false}
        />
        <YAxis
          domain={[-domainPadding, domainPadding]}
          tick={{ fill: "#566073", fontSize: 11, fontFamily: "JetBrains Mono" }}
          axisLine={false}
          tickLine={false}
          width={56}
          tickFormatter={(v) => formatUsd(v)}
        />
        <ReferenceLine y={0} stroke="#313c4d" />
        <Tooltip content={<CustomTooltip />} cursor={{ fill: "#ffffff08" }} />
        <Bar dataKey="pnl" radius={[1, 1, 1, 1]} minPointSize={2}>
          {data.map((entry, idx) => (
            <Cell key={idx} fill={entry.pnl >= 0 ? "#00e08f" : "#ff4d6d"} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
