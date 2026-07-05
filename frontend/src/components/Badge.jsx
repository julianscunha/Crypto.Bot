const TONE_CLASS = {
  positive: "badge--positive",
  negative: "badge--negative",
  warning: "badge--warning",
  neutral: "badge--neutral",
};

export function Badge({ children, tone = "neutral" }) {
  return <span className={`badge ${TONE_CLASS[tone]}`}>{children}</span>;
}
