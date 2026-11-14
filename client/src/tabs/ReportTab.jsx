import { useState } from "react";
import MarkdownLite from "../components/MarkdownLite.jsx";
import { Tag } from "../components/ui.jsx";

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
      window.setTimeout(() => setCopied(false), 1800);
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
    return <p className="fine-print">The report is not available for this analysis.</p>;
  }

  return (
    <div className="tab-stack">
      <div className="report-actions">
        <div>
          <p className="kicker">Deterministic template + optional grounded polish</p>
          <h2>Executive report</h2>
        </div>
        <div className="button-row">
          <button type="button" className="button secondary" onClick={copyReport}>
            {copied ? "Copied" : "Copy markdown"}
          </button>
          <button type="button" className="button primary" onClick={downloadReport}>
            Download .md
          </button>
        </div>
      </div>

      <article className="panel report-panel">
        <div className="report-banner">
          <Tag tone="accent">evidence bullets cite a page</Tag>
          <Tag tone="neutral">{isDemo ? "demo fixture" : "live analysis"}</Tag>
        </div>
        <MarkdownLite text={markdown} />
      </article>

      <p className="syllabus-note">
        <span>CSR322 link</span> Natural language generation and grounded generation (CO5):
        only retrieved text reaches the report, and any sentence without a valid citation is
        dropped by a mechanical check.
      </p>
    </div>
  );
}
