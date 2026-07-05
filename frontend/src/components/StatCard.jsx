const TONE_CLASS = {
  positive: "stat-card--positive",
  negative: "stat-card--negative",
  warning: "stat-card--warning",
  neutral: "",
};

export function StatCard({ label, value, sublabel, tone = "neutral" }) {
  return (
    <div className={`stat-card ${TONE_CLASS[tone] || ""}`}>
      <span className="stat-card__label">{label}</span>
      <span className="stat-card__value">{value}</span>
      {sublabel && <span className="stat-card__sublabel">{sublabel}</span>}
    </div>
  );
}
