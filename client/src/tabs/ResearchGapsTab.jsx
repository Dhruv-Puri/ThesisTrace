import { useMemo, useState } from "react";
import { EmptyState, Tag } from "../components/ui.jsx";

const CATEGORIES = [
  { id: "author_reported", label: "Author-reported", color: "purple" },
  { id: "methodological", label: "Methodological", color: "blue" },
  { id: "evidence", label: "Evidence", color: "amber" },
];

function GapCard({ gap, index }) {
  const category = CATEGORIES.find((item) => item.id === gap.category);
  const [expanded, setExpanded] = useState(false);

  return (
    <article className={`gap-card gap-${category?.color || "blue"}`}>
      <div className="gap-card-top">
        <span className="gap-index">{String(index + 1).padStart(2, "0")}</span>
        <div className="gap-card-heading">
          <h3>{gap.title || "Research finding"}</h3>
          <span className="gap-location">
            {gap.section || "Section not identified"}
            {gap.page ? ` · Page ${gap.page}` : ""}
          </span>
        </div>
        <Tag tone={gap.confidence === "high" ? "accent" : "warn"}>
          {gap.confidence || "unrated"} confidence
        </Tag>
      </div>

      <p className="gap-description">{gap.description}</p>

      {(gap.claim || gap.evidence?.length) && (
        <button
          className="gap-expand"
          onClick={() => setExpanded(!expanded)}
          aria-expanded={expanded}
        >
          {expanded ? "Hide details" : "Explore evidence"}
          <span>{expanded ? "−" : "+"}</span>
        </button>
      )}

      {expanded && (
        <div className="gap-details">
          {gap.claim && (
            <div>
              <span className="gap-detail-label">RELATED CLAIM</span>
              <p>{gap.claim}</p>
            </div>
          )}
          {gap.evidence?.length > 0 && (
            <div>
              <span className="gap-detail-label">EVIDENCE DETAILS</span>
              {gap.evidence.map((item, i) => (
                <p key={i} className="gap-evidence-item">
                  {typeof item === "string" ? item : JSON.stringify(item)}
                </p>
              ))}
            </div>
          )}
        </div>
      )}

      <div className="gap-card-footer">
        <span>{String(gap.source || "Not specified").replace(/_/g, " ")}</span>
        <span>{category?.label || "Finding"}</span>
      </div>
    </article>
  );
}

export default function ResearchGapsTab({ analysis }) {
  const report = analysis?.research_gaps;
  const [activeFilter, setActiveFilter] = useState("all");

  const gaps = report?.gaps || [];
  const counts = report?.category_counts || {};

  const filteredGaps = useMemo(
    () =>
      activeFilter === "all"
        ? gaps
        : gaps.filter((gap) => gap.category === activeFilter),
    [gaps, activeFilter]
  );

  if (!report) {
    return (
      <EmptyState title="No research gap analysis">
        This analysis did not return research gap findings. Try analysing the
        paper again.
      </EmptyState>
    );
  }

  const total = report.total_gaps ?? gaps.length;

  return (
    <div className="tab-stack research-gaps">
      <section className="gap-hero">
        <div className="gap-hero-copy">
          <span className="gap-eyebrow">RESEARCH INTELLIGENCE / 01</span>
          <h2>What's still unexplored?</h2>
          <p>
            A closer look at limitations, methodological reporting and claims
            that need stronger evidence.
          </p>
        </div>
        <div className="gap-total">
          <strong>{total}</strong>
          <span>findings identified</span>
        </div>
      </section>

      <section className="gap-metrics">
        {CATEGORIES.map((category) => (
          <button
            key={category.id}
            className={`gap-metric ${category.color} ${
              activeFilter === category.id ? "selected" : ""
            }`}
            onClick={() =>
              setActiveFilter(
                activeFilter === category.id ? "all" : category.id
              )
            }
          >
            <span className="gap-metric-dot" />
            <span className="gap-metric-label">{category.label}</span>
            <strong>{counts[category.id] || 0}</strong>
            <span className="gap-metric-caption">Findings</span>
          </button>
        ))}
      </section>

      <section className="gap-explorer">
        <div className="gap-explorer-heading">
          <div>
            <span className="gap-eyebrow">FINDINGS EXPLORER</span>
            <h2>Explore the evidence</h2>
            <p>{filteredGaps.length} findings in this view</p>
          </div>
          <div className="gap-filters">
            <button
              className={activeFilter === "all" ? "active" : ""}
              onClick={() => setActiveFilter("all")}
            >
              All
            </button>
            {CATEGORIES.map((category) => (
              <button
                key={category.id}
                className={activeFilter === category.id ? "active" : ""}
                onClick={() => setActiveFilter(category.id)}
              >
                {category.label}
              </button>
            ))}
          </div>
        </div>

        {filteredGaps.length ? (
          <div className="gap-card-list">
            {filteredGaps.map((gap, index) => (
              <GapCard key={`${gap.category}-${index}`} gap={gap} index={index} />
            ))}
          </div>
        ) : (
          <EmptyState title="No findings in this category">
            No findings of this type were identified in the current analysis.
          </EmptyState>
        )}
      </section>

      {report.limitations?.length > 0 && (
        <section className="gap-safeguards">
          <span className="gap-eyebrow">SCIENTIFIC INTERPRETATION</span>
          <h2>Read these findings carefully</h2>
          <ul>
            {report.limitations.map((item, index) => (
              <li key={index}>{item}</li>
            ))}
          </ul>
        </section>
      )}
    </div>
  );
}
