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
