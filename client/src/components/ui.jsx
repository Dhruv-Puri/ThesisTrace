const ICON_PATHS = {
  overview: (
    <>
      <path d="M4 19.5V4.5" />
      <path d="M4 19.5h16" />
      <path d="M7.5 14.5l3.5-4 2.5 2.5L18 7.5" />
      <circle cx="18" cy="7.5" r="1.1" />
    </>
  ),
  concepts: (
    <>
      <path d="M20.6 13.1 11.2 3.7A2 2 0 0 0 9.8 3.1H5a2 2 0 0 0-2 2v4.8a2 2 0 0 0 .6 1.4l9.4 9.4a2 2 0 0 0 2.9 0l4.7-4.7a2 2 0 0 0 0-2.9z" />
      <circle cx="7.5" cy="7.5" r="1" />
    </>
  ),
  claims: (
    <>
      <path d="M12 3l7 2.8v6.4c0 4.2-2.9 7.2-7 8.8-4.1-1.6-7-4.6-7-8.8V5.8z" />
      <path d="m9 12 2.1 2.1L15.2 10" />
    </>
  ),
  repro: (
    <>
      <path d="M3.5 12a8.5 8.5 0 0 1 14.7-5.8l2.3 2.3" />
      <path d="M20.5 3.5v5h-5" />
      <path d="M20.5 12a8.5 8.5 0 0 1-14.7 5.8l-2.3-2.3" />
      <path d="M3.5 20.5v-5h5" />
    </>
  ),
  trl: (
    <>
      <path d="M7.5 2.5v19" />
      <path d="M16.5 2.5v19" />
      <path d="M7.5 6.5h9" />
      <path d="M7.5 11.5h9" />
      <path d="M7.5 16.5h9" />
    </>
  ),
  report: (
    <>
      <path d="M7 3h7l5 5v13H7z" />
      <path d="M14 3v5h5" />
      <path d="M10.5 13h5" />
      <path d="M10.5 16.5h5" />
    </>
  ),
  upload: (
    <>
      <path d="M12 15.5V4.5" />
      <path d="m7 9.5 5-5 5 5" />
      <path d="M4.5 20h15" />
    </>
  ),
};

export function Icon({ name, size = 16, className = "" }) {
  const paths = ICON_PATHS[name];
  if (!paths) return null;
  return (
    <svg
      className={`icon ${className}`.trim()}
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      {paths}
    </svg>
  );
}

export function StatCard({ label, value, detail, tone = "" }) {
  return (
    <article className={`stat-card ${tone ? `tone-${tone}` : ""}`}>
      <p className="stat-label">{label}</p>
      <p className="stat-value">{value}</p>
      {detail ? <p className="stat-detail">{detail}</p> : null}
    </article>
  );
}

export function Tag({ children, tone = "neutral" }) {
  return <span className={`tag tag-${tone}`}>{children}</span>;
}

export function VerdictPill({ verdict }) {
  const meta = {
    supported: { label: "Supported", tone: "supported" },
    partially_supported: { label: "Partially supported", tone: "partial" },
    insufficient: { label: "Insufficient evidence", tone: "insufficient" },
  }[verdict] || { label: "Not checked", tone: "neutral" };
  return (
    <span className={`verdict verdict-${meta.tone}`}>
      <span className="verdict-dot" aria-hidden="true" />
      {meta.label}
    </span>
  );
}

export function ReproStatus({ status }) {
  const meta = {
    yes: { label: "Present", symbol: "✓", tone: "supported" },
    partial: { label: "Partial", symbol: "≈", tone: "partial" },
    no: { label: "Missing", symbol: "✕", tone: "insufficient" },
  }[status] || { label: "Unknown", symbol: "?", tone: "neutral" };
  return (
    <span className={`repro-status repro-${meta.tone}`}>
      <span aria-hidden="true">{meta.symbol}</span> {meta.label}
    </span>
  );
}

export function EmptyState({ title, children }) {
  return (
    <div className="empty-state">
      <span className="empty-mark" aria-hidden="true">∅</span>
      <h3>{title}</h3>
      {children ? <p>{children}</p> : null}
    </div>
  );
}

export function formatNumber(value) {
  if (value === null || value === undefined || value === "") return "—";
  const number = Number(value);
  return Number.isFinite(number) ? new Intl.NumberFormat("en-US").format(number) : String(value);
}

export function formatPercent(value) {
  const number = Number(value);
  return Number.isFinite(number) ? `${Math.round(number * 100)}%` : "—";
}

export const TYPE_LABELS = {
  PER: "People",
  ORG: "Organisations",
  LOC: "Locations",
  DATASET: "Datasets",
  METRIC: "Metrics",
  MODEL: "Models",
  ALGORITHM: "Methods",
  HARDWARE: "Hardware",
  TECH: "Technical concepts",
  DRUG: "Drugs",
  MATERIAL: "Materials",
};
