export function Panel({ title, eyebrow, action, children, className = "" }) {
  return (
    <section className={`panel ${className}`}>
      {(title || eyebrow || action) && (
        <header className="panel__header">
          <div>
            {eyebrow && <span className="panel__eyebrow">{eyebrow}</span>}
            {title && <h2 className="panel__title">{title}</h2>}
          </div>
          {action && <div className="panel__action">{action}</div>}
        </header>
      )}
      <div className="panel__body">{children}</div>
    </section>
  );
}
