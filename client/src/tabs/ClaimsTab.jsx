import { useState } from "react";
import { getAudit } from "../api.js";
import { EmptyState, Icon, Meter, VerdictPill, formatPercent } from "../components/ui.jsx";

const FILTERS = [
  { id: "all", label: "All" },
  { id: "supported", label: "Supported" },
  { id: "partially_supported", label: "Partial" },
  { id: "insufficient", label: "Unverified" },
];

const METHOD_LABELS = {
  nli: "NLI cross-encoder",
  "lexical-fallback": "Lexical fallback",
  "retrieval-only": "Retrieval only",
  unknown: "Unknown",
};

function downloadJson(payload, filename) {
  const blob = new Blob([JSON.stringify(payload, null, 2)], {
    type: "application/json;charset=utf-8",
  });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

function Receipt({ claim }) {
  const audit = claim.audit;
  const evidence = claim.evidence || [];

  if (!audit) {
    return (
      <div className="receipt-body">
        <p className="muted">No receipt was stored for this verdict.</p>
      </div>
    );
  }

  const top = audit.retrieval?.candidates?.[0];
  const thresholds = audit.nli?.thresholds;
  const method = METHOD_LABELS[audit.method] || audit.method;

  return (
    <div className="receipt-body">
      <dl className="receipt-grid">
        <div><dt>Method</dt><dd>{method}</dd></div>
        <div><dt>Confidence</dt><dd>{formatPercent(audit.confidence)}</dd></div>
        <div>
          <dt>Retrieval</dt>
          <dd>
            {top ? `top match ${formatPercent(top.score)} on p.${top.page}` : "no passage above the floor"}
          </dd>
        </div>
        {audit.nli ? (
          <div>
            <dt>NLI</dt>
            <dd>
              entailment {formatPercent(audit.nli.entailment)} · contradiction{" "}
              {formatPercent(audit.nli.contradiction)}
            </dd>
          </div>
        ) : null}
        {thresholds ? (
          <div>
            <dt>Thresholds</dt>
            <dd>
              supported ≥ {thresholds.supported_entailment} entailment, ≥{" "}
              {thresholds.supported_relevance} relevance
            </dd>
          </div>
        ) : null}
        {audit.nli?.model ? (
          <div><dt>Model</dt><dd>{audit.nli.model}</dd></div>
        ) : null}
        <div>
          <dt>Receipt</dt>
          <dd>
            pipeline {audit.pipeline_version} · {String(audit.checked_at || "").replace("T", " ")}
          </dd>
        </div>
      </dl>

      {(top || audit.nli) ? (
        <div className="receipt-meters">
          {top ? (
            <Meter label="Retrieval relevance" value={top.score} tone="accent" />
          ) : null}
          {audit.nli ? (
            <Meter label="Entailment" value={audit.nli.entailment} tone="supported" />
          ) : null}
          {audit.nli ? (
            <Meter label="Contradiction" value={audit.nli.contradiction} tone="insufficient" />
          ) : null}
        </div>
      ) : null}

      {audit.reason ? <p className="receipt-reason">{audit.reason}</p> : null}

      {evidence.length ? (
        <ol className="evidence">
          {evidence.map((item, index) => (
            <li key={`${claim.id}-ev-${index}`}>
              <span className="cite">p.{item.page}</span>
              <p>{item.text}</p>
            </li>
          ))}
        </ol>
      ) : null}
    </div>
  );
}

export default function ClaimsTab({ analysis }) {
  const [filter, setFilter] = useState("all");
  const [downloadError, setDownloadError] = useState("");
  const claims = analysis?.claims || [];
  const jobId = analysis?.job_id || "";
  const isDemo = !jobId || jobId.startsWith("demo");

  const counts = {
    all: claims.length,
    supported: claims.filter((claim) => claim.verdict === "supported").length,
    partially_supported: claims.filter((claim) => claim.verdict === "partially_supported").length,
    insufficient: claims.filter((claim) => claim.verdict === "insufficient").length,
  };
  const visible = filter === "all" ? claims : claims.filter((claim) => claim.verdict === filter);

  async function exportAudit() {
    if (isDemo) return;
    setDownloadError("");
    try {
      const audit = await getAudit(jobId);
      downloadJson(audit, `thesistrace-audit-${jobId.slice(0, 8)}.json`);
    } catch (error) {
      setDownloadError(error.message || "The audit could not be downloaded.");
    }
  }

  return (
    <div className="stack">
      <div className="toolbar">
        <div className="segmented" role="tablist" aria-label="Filter claims">
          {FILTERS.map((item) => (
            <button
              key={item.id}
              type="button"
              role="tab"
              aria-selected={filter === item.id}
              className={filter === item.id ? "is-active" : ""}
              onClick={() => setFilter(item.id)}
            >
              {item.label}
              <span>{counts[item.id]}</span>
            </button>
          ))}
        </div>
        {!isDemo && claims.length ? (
          <button type="button" className="text-button" onClick={exportAudit}>
            <Icon name="download" size={14} /> Audit file
          </button>
        ) : null}
      </div>

      {downloadError ? <p className="error-line">{downloadError}</p> : null}

      {claims.length ? (
        <div
          className="verdict-strip"
          role="img"
          aria-label={`${counts.supported} supported, ${counts.partially_supported} partial, ${counts.insufficient} unverified`}
        >
          {counts.supported ? (
            <span className="verdict-seg seg-supported" style={{ flexGrow: counts.supported }} />
          ) : null}
          {counts.partially_supported ? (
            <span className="verdict-seg seg-partial" style={{ flexGrow: counts.partially_supported }} />
          ) : null}
          {counts.insufficient ? (
            <span className="verdict-seg seg-insufficient" style={{ flexGrow: counts.insufficient }} />
          ) : null}
        </div>
      ) : null}

      {visible.length ? (
        <div className="claim-list">
          {visible.map((claim) => (
            <article className="claim" key={claim.id}>
              <div className="claim-line">
                <VerdictPill verdict={claim.verdict} />
                <p className="claim-text">{claim.text}</p>
                <span className="cite">p.{claim.page}</span>
              </div>
              {claim.note ? <p className="claim-note">{claim.note}</p> : null}
              <details className="disclosure receipt">
                <summary>Why this verdict?</summary>
                <Receipt claim={claim} />
              </details>
            </article>
          ))}
        </div>
      ) : (
        <EmptyState title={claims.length ? "Nothing in this bucket" : "No claims found"}>
          {claims.length
            ? "Every extracted claim falls under a different verdict."
            : "This document did not contain sentences that read as claims."}
        </EmptyState>
      )}
    </div>
  );
}
