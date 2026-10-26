import { useState } from "react";
import { EmptyState, VerdictPill, Tag, formatPercent } from "../components/ui.jsx";

const FILTERS = [
  { id: "all", label: "All claims" },
  { id: "supported", label: "Supported" },
  { id: "partially_supported", label: "Partial" },
  { id: "insufficient", label: "Insufficient" },
];

const NLI_LABELS = {
  entailment: "entailment",
  neutral: "neutral",
  contradiction: "contradiction",
  not_checked: "not sent to NLI",
};

function ClaimCard({ claim }) {
  const evidence = claim.evidence || [];
  const confidence = Math.round((Number(claim.confidence) || 0) * 100);
  return (
    <article className={`claim-card claim-${claim.verdict}`}>
      <div className="claim-top">
        <div>
          <div className="claim-meta">
            <Tag tone="neutral">{claim.claim_type}</Tag>
            <span>{claim.section || "Body"}</span>
            <span className="cite">[p.{claim.page}]</span>
            <span className="extraction-tag">{claim.extraction || "extracted"}</span>
          </div>
          <h3 className="claim-text">{claim.text}</h3>
        </div>
        <VerdictPill verdict={claim.verdict} />
      </div>

      <div className="confidence">
        <div className="confidence-head">
          <span>Confidence</span>
          <strong>{confidence}%</strong>
        </div>
        <div className="confidence-track">
          <div className={`confidence-fill fill-${claim.verdict}`} style={{ width: `${confidence}%` }} />
        </div>
      </div>

      {claim.note ? <p className="claim-note">{claim.note}</p> : null}

      <div className="evidence">
        <div className="evidence-head">
          <span>{claim.verdict === "insufficient" ? "Passages searched" : "Evidence used"}</span>
          <span>{evidence.length} passage{evidence.length === 1 ? "" : "s"}</span>
        </div>
        {evidence.length ? (
          evidence.map((item, index) => (
            <div className="evidence-row" key={`${claim.id}-ev-${index}`}>
              <div className="evidence-top">
                <span className="cite">[p.{item.page}]</span>
                <span className={`nli-pill nli-${item.nli || "neutral"}`}>
                  {NLI_LABELS[item.nli] || item.nli || "related"}
                </span>
                <span className="relevance">{formatPercent(item.relevance)} match</span>
                {item.nli_score ? (
                  <span className="fine-print">NLI {formatPercent(item.nli_score)}</span>
                ) : null}
              </div>
              <p>{item.text}</p>
            </div>
          ))
        ) : (
          <p className="fine-print">
            Nothing cleared the retrieval floor. The verdict is “insufficient evidence”, not
            “false”.
          </p>
        )}
      </div>
    </article>
  );
}

export default function ClaimCheckTab({ analysis }) {
  const [filter, setFilter] = useState("all");
  const claims = analysis?.claims || [];
  const counts = {
    all: claims.length,
    supported: claims.filter((claim) => claim.verdict === "supported").length,
    partially_supported: claims.filter((claim) => claim.verdict === "partially_supported").length,
    insufficient: claims.filter((claim) => claim.verdict === "insufficient").length,
  };
  const visible = filter === "all" ? claims : claims.filter((claim) => claim.verdict === filter);

  return (
    <div className="tab-stack">
      <section className="method-callout">
        <div>
          <p className="kicker">CO5 · RAG grounding</p>
          <h2>Retrieve first. Verify second. Never let the LLM decide.</h2>
        </div>
        <p>
          Each claim is used as a query against the paper’s own sentences (TF-IDF). The
          strongest passages are sent to a local NLI cross-encoder, which labels entailment,
          neutrality or contradiction. The language model may write prose, but it never
          assigns a verdict.
        </p>
      </section>

      <div className="filter-row" role="tablist" aria-label="Filter claims by verdict">
        {FILTERS.map((item) => (
          <button
            key={item.id}
            type="button"
            role="tab"
            aria-selected={filter === item.id}
            className={`filter ${filter === item.id ? "filter-active" : ""}`}
            onClick={() => setFilter(item.id)}
          >
            {item.label}
            <span>{counts[item.id]}</span>
          </button>
        ))}
      </div>

      {visible.length ? (
        <div className="claim-list">
          {visible.map((claim) => (
            <ClaimCard claim={claim} key={claim.id} />
          ))}
        </div>
      ) : (
        <EmptyState title={claims.length ? "No claims in this bucket" : "No claims extracted"}>
          {claims.length
            ? "Try another filter, or read the report for the overall picture."
            : "The heuristic found no result-like sentences. The document may be a review, an abstract-only page, or mostly background."}
        </EmptyState>
      )}

      <p className="syllabus-note">
        <span>CSR322 link</span> Text classification and semantic analysis; zero-shot NLI
        (Practical 3), evidence retrieval for RAG (CO5), and hallucination checks (CO4).
      </p>
    </div>
  );
}
