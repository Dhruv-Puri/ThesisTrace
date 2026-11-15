import { useState } from "react";
import MarkdownLite from "../components/MarkdownLite.jsx";
import { Icon, Tag, firstSentence } from "../components/ui.jsx";

const READINESS_CALLS = {
  1: "Too early to build",
  2: "Concept stage — keep watching",
  3: "Proof of concept only",
  4: "Lab-validated — pilot next",
  5: "Ready for a relevant-environment pilot",
  6: "Ready for an operational demonstration",
  7: "Operational prototype — pilot with users",
  8: "Qualified system — deployment review",
  9: "Proven in operation",
};

const NEXT_STEPS = {
  1: "Define a testable prototype.",
  2: "Turn the concept into a lab experiment.",
  3: "Prove the core result in a controlled setting.",
  4: "Run a pilot in a relevant environment.",
  5: "Demonstrate the system with real data.",
  6: "Pilot with users and measure the outcome.",
  7: "Run an operational pilot with a partner.",
  8: "Complete a deployment and security review.",
  9: "Move to procurement and scale-up.",
};

function clip(text, limit = 150) {
  const clean = String(text || "").replace(/\s+/g, " ").trim();
  return clean.length > limit ? `${clean.slice(0, limit - 1)}…` : clean;
}

function DecisionBrief({ analysis }) {
  const claims = analysis?.claims || [];
  const supported = claims.filter((claim) => claim.verdict === "supported");
  const partial = claims.filter((claim) => claim.verdict === "partially_supported").length;
  const insufficient = claims.filter((claim) => claim.verdict === "insufficient").length;
  const items = analysis?.reproducibility?.items || [];
  const gaps = items.filter((item) => item.status !== "yes");
  const missing = items.filter((item) => item.status === "no").length;
  const level = Math.min(9, Math.max(1, Number(analysis?.trl?.level) || 1));
  const strongest = supported[0];
  const biggestGap = gaps.find((item) => item.status === "no") || gaps[0];

  return (
    <section className="brief">
      <div className="brief-head">
        <div>
          <p className="eyebrow">Decision brief</p>
          <h2>{READINESS_CALLS[level]}</h2>
          <p className="muted">
            {firstSentence(analysis?.trl?.why, "Readiness is based on the paper's own wording.")}
          </p>
        </div>
        <Tag tone="accent">TRL {level}/9</Tag>
      </div>

      <div className="brief-grid">
        <div className="brief-item">
          <span className="brief-label">Evidence</span>
          <strong>{supported.length} of {claims.length} claims supported</strong>
          <p>
            {strongest
              ? `“${clip(strongest.text)}” [p.${strongest.evidence?.[0]?.page ?? strongest.page}]`
              : "No claim cleared the evidence threshold."}
          </p>
        </div>
        <div className="brief-item">
          <span className="brief-label">Gaps</span>
          <strong>
            {missing} of {items.length} signals missing
            {partial ? ` · ${partial} partial` : ""}
          </strong>
          <p>{biggestGap ? `${biggestGap.name}: ${clip(biggestGap.evidence, 110)}` : "Every checked signal is present."}</p>
        </div>
        <div className="brief-item">
          <span className="brief-label">Next step</span>
          <strong>{NEXT_STEPS[level]}</strong>
          <p>{analysis?.trl?.note || "Attach this brief to a review or funding decision."}</p>
        </div>
      </div>

      <p className="brief-note">
        A reading of the evidence in this report, not an investment recommendation.
        {insufficient ? ` ${insufficient} claim${insufficient === 1 ? " is" : "s are"} still unverified.` : ""}
      </p>
    </section>
  );
}

function downloadBlob(markdown, filename) {
  const blob = new Blob([markdown], { type: "text/markdown;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

export default function ReportTab({ analysis }) {
  const [copied, setCopied] = useState(false);
  const markdown = analysis?.report?.markdown || "";
  const title = analysis?.doc?.title || "paper";
  const jobId = analysis?.job_id || "";
  const isDemo = !jobId || jobId.startsWith("demo");

  async function copyReport() {
    try {
      await navigator.clipboard.writeText(markdown);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1600);
    } catch {
      setCopied(false);
    }
  }

  function downloadReport() {
    if (!markdown) return;
    if (!isDemo) {
      const link = document.createElement("a");
      link.href = `/api/jobs/${encodeURIComponent(jobId)}/report?format=md`;
      link.download = `${title.replace(/[^A-Za-z0-9]+/g, "-").slice(0, 50) || "paper"}-report.md`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      return;
    }
    downloadBlob(markdown, "thesistrace-report.md");
  }

  if (!markdown) {
    return <p className="muted">The report is not available for this analysis.</p>;
  }

  return (
    <div className="stack">
      <DecisionBrief analysis={analysis} />

      <div className="block-head">
        <div>
          <h2>Executive report</h2>
          <p className="muted">Every evidence bullet cites a page.</p>
        </div>
        <div className="button-row">
          <button type="button" className="button quiet" onClick={copyReport}>
            {copied ? "Copied" : "Copy"}
          </button>
          <button type="button" className="button" onClick={downloadReport}>
            <Icon name="download" size={15} /> Download .md
          </button>
        </div>
      </div>
      <article className="report">
        <MarkdownLite text={markdown} />
      </article>
    </div>
  );
}
