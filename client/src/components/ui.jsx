const ICON_PATHS = {
  summary: (
    <>
      <path d="M6 3.5h9l4 4V20.5H6z" />
      <path d="M15 3.5v4h4" />
      <path d="M9 11.5h7M9 15h7M9 18h4" />
    </>
  ),
  claims: (
    <>
      <path d="M12 3.2 19 6v6.1c0 4.1-2.9 7.1-7 8.7-4.1-1.6-7-4.6-7-8.7V6z" />
      <path d="m9 12 2.1 2.1L15.3 10" />
    </>
  ),
  readiness: (
    <>
      <path d="M5 20.5V15M10 20.5V10.5M15 20.5V7M20 20.5V4" />
    </>
  ),
  report: (
    <>
      <path d="M6 3.5h9l4 4V20.5H6z" />
      <path d="M15 3.5v4h4" />
      <path d="M9 13h7M9 16.5h5" />
    </>
  ),
  portfolio: (
    <>
      <path d="M4 8.5 12 4l8 4.5-8 4.5z" />
      <path d="m4 12.5 8 4.5 8-4.5" />
      <path d="m4 16.5 8 4.5 8-4.5" />
    </>
  ),
  chat: (
    <>
      <path d="M4.5 5.5h15v10h-9l-4 3.5v-3.5h-2z" />
      <path d="M8 9.5h8M8 12.5h5" />
    </>
  ),
  upload: (
    <>
      <path d="M12 15.5V4.5" />
      <path d="m7 9.5 5-5 5 5" />
      <path d="M4.5 20h15" />
    </>
  ),
  close: (
    <>
      <path d="m6 6 12 12M18 6 6 18" />
    </>
  ),
  download: (
    <>
      <path d="M12 4.5v11" />
      <path d="m7 10.5 5 5 5-5" />
      <path d="M4.5 20h15" />
    </>
  ),
  arrow: (
    <>
      <path d="M4.5 12h15" />
      <path d="m14 6.5 5.5 5.5-5.5 5.5" />
    </>
  ),
  help: (
    <>
      <circle cx="12" cy="12" r="9" />
      <path d="M9.5 9.5a2.5 2.5 0 0 1 4.5 1.5c0 1.5-2 2-2 3" />
      <circle cx="12" cy="17" r="0.5" fill="currentColor" />
    </>
  ),
  sparkles: (
    <>
      <path d="m12 3 2 5 5 2-5 2-2 5-2-5-5-2 5-2z" />
      <path d="M19 16l1 2.5 2.5 1-2.5 1-1 2.5-1-2.5-2.5-1 2.5-1z" />
    </>
  ),
  lightbulb: (
    <>
      <path d="M9 18h6M10 22h4M12 2a7 7 0 0 0-4.5 12.3c.7.6 1.5 1.7 1.5 2.7h6c0-1-.8-2.1-1.5-2.7A7 7 0 0 0 12 2z" />
    </>
  ),
  settings: (
    <>
      <circle cx="12" cy="12" r="3" />
      <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z" />
    </>
  ),
  pricing: (
    <>
      <path d="M6 3h12l4 6-10 12L2 9z" />
      <path d="M2 9h20M12 21 8.5 9M12 21l3.5-12M6.5 3 10 9M17.5 3 14 9" />
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

export function VerdictPill({ verdict, compact = false }) {
  const meta = {
    supported: { label: "Supported", tone: "supported" },
    partially_supported: { label: compact ? "Partial" : "Partially supported", tone: "partial" },
    insufficient: { label: compact ? "Unverified" : "Insufficient evidence", tone: "insufficient" },
  }[verdict] || { label: "Not checked", tone: "neutral" };
  return (
    <span className={`verdict verdict-${meta.tone}`}>
      <span className="verdict-dot" aria-hidden="true" />
      {meta.label}
    </span>
  );
}

export function Tag({ children, tone = "neutral" }) {
  return <span className={`tag tag-${tone}`}>{children}</span>;
}

export function StatusMark({ status }) {
  const meta = {
    yes: { label: "Present", tone: "supported" },
    partial: { label: "Partial", tone: "partial" },
    no: { label: "Missing", tone: "insufficient" },
  }[status] || { label: "Unknown", tone: "neutral" };
  return (
    <span className={`status status-${meta.tone}`}>
      <span className="status-dot" aria-hidden="true" />
      {meta.label}
    </span>
  );
}

export function EmptyState({ title, children }) {
  return (
    <div className="empty">
      <h3>{title}</h3>
      {children ? <p>{children}</p> : null}
    </div>
  );
}

export function RingGauge({ value = 0, max = 100, label, display, sublabel, tone = "accent", size = 96 }) {
  const safeMax = Number(max) > 0 ? Number(max) : 1;
  const ratio = Math.max(0, Math.min(1, (Number(value) || 0) / safeMax));
  const radius = 46;
  const circumference = 2 * Math.PI * radius;
  const shown = display ?? Math.round(ratio * 100);
  return (
    <div
      className={`ring-wrap ring-${tone}`}
      style={{ "--ring-size": `${size}px` }}
      role="img"
      aria-label={`${label || "Value"}: ${shown}${sublabel || ""}`}
    >
      <div className="ring">
        <svg viewBox="0 0 100 100" aria-hidden="true">
          <circle className="ring-track" cx="50" cy="50" r={radius} />
          <circle
            className="ring-value"
            cx="50"
            cy="50"
            r={radius}
            strokeDasharray={circumference}
            strokeDashoffset={circumference * (1 - ratio)}
            style={{
              "--ring-circumference": circumference,
              "--ring-offset": circumference * (1 - ratio),
            }}
          />
        </svg>
        <span className="ring-text">
          <strong>{shown}</strong>
          {sublabel ? <small>{sublabel}</small> : null}
        </span>
      </div>
      {label ? <span className="ring-label">{label}</span> : null}
    </div>
  );
}

export function Meter({ label, value, tone = "accent", detail }) {
  const ratio = Math.max(0, Math.min(1, Number(value) || 0));
  return (
    <div className="meter">
      <div className="meter-head">
        <span>{label}</span>
        <span className="meter-value">{detail ?? `${Math.round(ratio * 100)}%`}</span>
      </div>
      <div className="meter-track">
        <span className={`meter-fill meter-${tone}`} style={{ width: `${ratio * 100}%` }} />
      </div>
    </div>
  );
}

export function LevelScale({ level = 0, max = 9 }) {
  const safeLevel = Math.max(0, Math.min(max, Number(level) || 0));
  return (
    <span className="level-scale" aria-hidden="true">
      {Array.from({ length: max }, (_, index) => (
        <span key={index} className={index < safeLevel ? "is-on" : ""} />
      ))}
    </span>
  );
}

export function CoverageRadar({ data, max = 10, label = "Content coverage" }) {
  const items = Array.isArray(data) ? data.filter((item) => Number.isFinite(Number(item.value))) : [];
  if (!items.length) return null;

  const width = 380;
  const height = 270;
  const cx = width / 2;
  const cy = height / 2;
  const radius = 84;
  const step = (Math.PI * 2) / items.length;
  const angleAt = (index) => -Math.PI / 2 + index * step;
  const point = (index, ratio) => [
    cx + Math.cos(angleAt(index)) * radius * ratio,
    cy + Math.sin(angleAt(index)) * radius * ratio,
  ];
  const polygon = (ratio) =>
    items.map((_, index) => point(index, ratio).map((value) => value.toFixed(1)).join(",")).join(" ");
  const areaPoints = items
    .map((item, index) =>
      point(index, Math.max(0, Math.min(1, Number(item.value) / max)))
        .map((value) => value.toFixed(1))
        .join(",")
    )
    .join(" ");

  return (
    <svg
      className="coverage-radar"
      viewBox={`0 0 ${width} ${height}`}
      role="img"
      aria-label={`${label}: ${items.map((item) => `${item.label} ${item.value} of ${max}`).join(", ")}`}
    >
      <g>
        {[0.25, 0.5, 0.75, 1].map((ratio) => (
          <polygon key={ratio} className="radar-grid" points={polygon(ratio)} />
        ))}
        {items.map((item, index) => {
          const [x, y] = point(index, 1);
          const [lx, ly] = point(index, 1.16);
          const cos = Math.cos(angleAt(index));
          const anchor = Math.abs(cos) < 0.2 ? "middle" : cos > 0 ? "start" : "end";
          return (
            <g key={item.label}>
              <line className="radar-axis" x1={cx} y1={cy} x2={x} y2={y} />
              <text
                className="radar-label"
                x={lx}
                y={ly + 3}
                textAnchor={anchor}
              >
                {item.label}
              </text>
            </g>
          );
        })}
        <polygon className="radar-area" points={areaPoints} />
        {items.map((item, index) => {
          const [x, y] = point(index, Math.max(0, Math.min(1, Number(item.value) / max)));
          return (
            <circle key={`dot-${item.label}`} className="radar-dot" cx={x} cy={y} r="2.6">
              <title>{`${item.label}: ${item.value}/${max}`}</title>
            </circle>
          );
        })}
      </g>
    </svg>
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

export function firstSentence(text, fallback = "") {
  const clean = String(text || "").trim();
  if (!clean) return fallback;
  const match = clean.match(/^(.+?[.!?])(\s|$)/);
  return match ? match[1] : clean;
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
  TECH: "Concepts",
  DRUG: "Drugs",
  MATERIAL: "Materials",
};
