const PATHS = {
  warning: (
    <path d="M12 3.5 21.5 20h-19L12 3.5Zm0 5.5v5m0 3h.01" />
  ),
  lock: (
    <>
      <rect x="5" y="11" width="14" height="10" rx="1.5" />
      <path d="M8 11V7.5a4 4 0 0 1 8 0V11" />
    </>
  ),
  check: <path d="M4 12.5 9.5 18 20 6" />,
  cross: <path d="M6 6 18 18M18 6 6 18" />,
  hourglass: (
    <path d="M6 3.5h12M6 20.5h12M7 3.5v3.2c0 1.5 5 4.3 5 5.3s-5 3.8-5 5.3v3.2M17 3.5v3.2c0 1.5-5 4.3-5 5.3s5 3.8 5 5.3v3.2" />
  ),
};

// Ícones SVG minimalistas — substituem emoji (⚠ 🔒 ✓ ✗ ⏳) para
// renderização consistente entre SO e leitura correta por screen reader.
export function Icon({ name, size = 14, label, className = "" }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={2}
      strokeLinecap="round"
      strokeLinejoin="round"
      className={`icon ${className}`}
      role={label ? "img" : "presentation"}
      aria-label={label}
      aria-hidden={label ? undefined : true}
    >
      {PATHS[name]}
    </svg>
  );
}
