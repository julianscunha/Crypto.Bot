function ReasonRow({ label, count, tone }) {
  return (
    <div className="reason-row">
      <span className={`reason-row__dot reason-row__dot--${tone}`} />
      <span className="reason-row__label">{label}</span>
      <span className="reason-row__count mono">{count}</span>
    </div>
  );
}

export function EventLog({ runtime }) {
  const blocked = runtime?.blocked_signal_reasons || {};
  const executed = runtime?.execution_reasons || {};

  const blockedEntries = Object.entries(blocked).sort((a, b) => b[1] - a[1]);
  const executedEntries = Object.entries(executed).sort((a, b) => b[1] - a[1]);

  const hasAny = blockedEntries.length > 0 || executedEntries.length > 0;

  if (!hasAny) {
    return (
      <div className="empty-state">
        No signal activity recorded yet this session.
      </div>
    );
  }

  return (
    <div className="event-log">
      {executedEntries.length > 0 && (
        <div className="event-log__group">
          <span className="event-log__group-title tone-positive">
            EXECUTION
          </span>
          {executedEntries.map(([reason, count]) => (
            <ReasonRow key={reason} label={reason} count={count} tone="positive" />
          ))}
        </div>
      )}

      {blockedEntries.length > 0 && (
        <div className="event-log__group">
          <span className="event-log__group-title tone-warning">
            BLOCKED SIGNALS
          </span>
          {blockedEntries.map(([reason, count]) => (
            <ReasonRow key={reason} label={reason} count={count} tone="warning" />
          ))}
        </div>
      )}
    </div>
  );
}
