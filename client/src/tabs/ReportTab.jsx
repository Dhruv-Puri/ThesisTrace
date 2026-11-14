import { useState } from "react";
import MarkdownLite from "../components/MarkdownLite.jsx";
import { Icon } from "../components/ui.jsx";

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
