import { useEffect, useState } from "react";
import MOCK_ANALYSIS from "./mocks/paperAnalysis.json";
import { getConfig, getJob, uploadPaper } from "./api.js";
import { Icon } from "./components/ui.jsx";
import PortfolioScreen from "./components/PortfolioScreen.jsx";
import ChatSheet, { useChat } from "./tabs/ChatSheet.jsx";
import ClaimsTab from "./tabs/ClaimsTab.jsx";
import ReadinessTab from "./tabs/ReadinessTab.jsx";
import ReportTab from "./tabs/ReportTab.jsx";
import SummaryTab from "./tabs/SummaryTab.jsx";

const MAX_MB = 30;
const ALLOWED = ["pdf", "txt", "md"];
const STORE_KEY = "thesistrace.analyses.v1";
const MAX_SAVED = 8;

const TABS = [
  { id: "summary", label: "Summary" },
  { id: "claims", label: "Claims" },
  { id: "readiness", label: "Readiness" },
  { id: "report", label: "Report" },
];

function validateFile(file) {
  const extension = file.name.split(".").pop()?.toLowerCase() || "";
  if (!ALLOWED.includes(extension)) return "Use a PDF, .txt or .md file.";
  if (file.size === 0) return "That file is empty.";
  if (file.size > MAX_MB * 1024 * 1024) return `Maximum upload size is ${MAX_MB} MB.`;
  return "";
}

function readSaved() {
  try {
    const raw = window.localStorage.getItem(STORE_KEY);
    const parsed = raw ? JSON.parse(raw) : [];
    return Array.isArray(parsed) ? parsed.filter((item) => item?.job_id) : [];
  } catch {
    return [];
  }
}

function writeSaved(list) {
  try {
    window.localStorage.setItem(STORE_KEY, JSON.stringify(list));
  } catch {
    /* private mode: the session still compares what is in memory */
  }
}

function entryFor(analysis) {
  const claims = analysis.claims || [];
  return {
    job_id: analysis.job_id,
    title: analysis.doc?.title || analysis.doc?.filename || "Untitled paper",
    pages: analysis.doc?.pages || 0,
    trl: analysis.trl?.level ?? null,
    repro: analysis.reproducibility?.score ?? null,
    supported: claims.filter((claim) => claim.verdict === "supported").length,
    claims: claims.length,
    saved_at: new Date().toISOString(),
  };
}

function Dropzone({ onFile, busy }) {
  const [dragging, setDragging] = useState(false);

  return (
    <label
      className={`dropzone ${dragging ? "is-dragging" : ""} ${busy ? "is-busy" : ""}`}
      htmlFor="paper-upload"
      onDragOver={(event) => {
        event.preventDefault();
        if (!busy) setDragging(true);
      }}
      onDragLeave={() => setDragging(false)}
      onDrop={(event) => {
        event.preventDefault();
        setDragging(false);
        const file = event.dataTransfer.files?.[0];
        if (file && !busy) onFile(file);
      }}
    >
      <input
        id="paper-upload"
        className="visually-hidden"
        type="file"
        accept=".pdf,.txt,.md,application/pdf,text/plain,text/markdown"
        disabled={busy}
        onChange={(event) => {
          const file = event.target.files?.[0];
          if (file) onFile(file);
          event.target.value = "";
        }}
      />
      <span className="drop-icon" aria-hidden="true"><Icon name="upload" size={20} /></span>
      <span className="drop-copy">
        <strong>{busy ? "Uploading…" : "Drop a paper here"}</strong>
        <span>PDF or plain text · up to {MAX_MB} MB</span>
      </span>
      <span className="button quiet">{busy ? "Working" : "Choose file"}</span>
    </label>
  );
}

function StartScreen({ onFile, onDemo, busy }) {
  return (
    <main className="start">
      <header className="brand">
        <span className="brand-mark" aria-hidden="true">T</span>
        ThesisTrace
      </header>

      <section className="start-main">
        <p className="eyebrow">Research readiness</p>
        <h1>Should this paper<br />become a product?</h1>
        <p className="lede">
          Upload a paper. See which claims its own evidence supports, whether it can be
          rebuilt, and how close it is to real-world use.
        </p>
        <Dropzone onFile={onFile} busy={busy} />
        <button type="button" className="text-button sample-link" onClick={onDemo}>
          See a sample analysis <Icon name="arrow" size={14} />
        </button>
      </section>

      <footer className="start-foot">Runs locally. No API key required.</footer>
    </main>
  );
}

function ProgressScreen({ job, uploading }) {
  const progress = Math.max(uploading ? 2 : 0, Number(job?.progress) || 0);
  return (
    <main className="center">
      <section className="progress-card" aria-live="polite">
        <p className="eyebrow">{uploading ? "Uploading" : "Reading the paper"}</p>
        <h1>{uploading ? "One moment" : "Working through it"}</h1>
        <p className="file">{job?.filename || "your document"}</p>
        <div
          className="bar"
          role="progressbar"
          aria-valuenow={progress}
          aria-valuemin={0}
          aria-valuemax={100}
        >
          <span style={{ width: `${Math.max(progress, 2)}%` }} />
        </div>
        <div className="bar-meta">
          <span>{job?.stage || (uploading ? "Uploading" : "Queued")}</span>
          <span>{progress}%</span>
        </div>
        <p className="muted">Usually 15–45 seconds.</p>
      </section>
    </main>
  );
}

function ErrorScreen({ message, onReset }) {
  return (
    <main className="center">
      <section className="progress-card">
        <p className="eyebrow">Nothing was analysed</p>
        <h1>That didn’t work</h1>
        <p className="lede">{message}</p>
        <button type="button" className="button" onClick={onReset}>Try another paper</button>
      </section>
    </main>
  );
}

function AnalysisHeader({ analysis, isDemo, canCompare, chatEnabled, onChat, onCompare, onReset }) {
  const claims = analysis.claims || [];
  const supported = claims.filter((claim) => claim.verdict === "supported").length;
  const trl = analysis.trl?.level ?? "—";
  const repro = analysis.reproducibility?.score ?? "—";

  return (
    <header className="analysis-head">
      <div className="head-copy">
        <p className="eyebrow">
          {isDemo ? "Sample analysis" : "Analysis"} · {analysis.doc?.pages || 0} pages
        </p>
        <h1>{analysis.doc?.title || "Untitled paper"}</h1>
        <p className="verdict-line">
          {supported} of {claims.length} claims supported
          <span aria-hidden="true"> · </span>TRL {trl}/9
          <span aria-hidden="true"> · </span>reproducibility {repro}/100
        </p>
        {!chatEnabled && !isDemo ? (
          <p className="head-note">Ask needs a Gemini key; everything else runs locally.</p>
        ) : null}
      </div>
      <div className="head-actions">
        {canCompare ? (
          <button type="button" className="button quiet" onClick={onCompare}>
            <Icon name="portfolio" size={15} /> Compare
          </button>
        ) : null}
        <button
          type="button"
          className="button quiet"
          onClick={onChat}
          disabled={!chatEnabled}
          title={chatEnabled ? "Ask a question about this paper" : "Add a Gemini key to ask questions"}
        >
          <Icon name="chat" size={15} /> Ask
        </button>
        <button type="button" className="button" onClick={onReset}>New paper</button>
      </div>
    </header>
  );
}

function Analysis({ analysis, tab, setTab, isDemo, canCompare, chatEnabled, onChat, onCompare, onReset }) {
  return (
    <main className="analysis">
      <AnalysisHeader
        analysis={analysis}
        isDemo={isDemo}
        canCompare={canCompare}
        chatEnabled={chatEnabled}
        onChat={onChat}
        onCompare={onCompare}
        onReset={onReset}
      />

      <nav className="tabs" role="tablist" aria-label="Analysis sections">
        {TABS.map((item) => (
          <button
            key={item.id}
            type="button"
            role="tab"
            aria-selected={tab === item.id}
            className={tab === item.id ? "is-active" : ""}
            onClick={() => setTab(item.id)}
          >
            {item.label}
          </button>
        ))}
      </nav>

      <section className="panel-area">
        {tab === "summary" ? <SummaryTab analysis={analysis} /> : null}
        {tab === "claims" ? <ClaimsTab analysis={analysis} /> : null}
        {tab === "readiness" ? <ReadinessTab analysis={analysis} /> : null}
        {tab === "report" ? <ReportTab analysis={analysis} /> : null}
      </section>

      {analysis.warnings?.length ? (
        <details className="method-notes">
          <summary>Method notes</summary>
          <ul>
            {analysis.warnings.map((warning, index) => (
              <li key={`warning-${index}`}>{warning}</li>
            ))}
          </ul>
        </details>
      ) : null}
    </main>
  );
}

export default function App() {
  const [phase, setPhase] = useState("start");
  const [analysis, setAnalysis] = useState(null);
  const [job, setJob] = useState(null);
  const [jobId, setJobId] = useState(null);
  const [error, setError] = useState("");
  const [config, setConfig] = useState(null);
  const [saved, setSaved] = useState(readSaved);
  const [tab, setTab] = useState("summary");
  const [chatOpen, setChatOpen] = useState(false);
  const chat = useChat(analysis?.job_id || "");

  useEffect(() => {
    getConfig().then(setConfig).catch(() => setConfig(null));
  }, []);

  useEffect(() => {
    if (phase !== "working" || !jobId) return undefined;
    let cancelled = false;
    let timer = null;

    async function poll() {
      try {
        const data = await getJob(jobId);
        if (cancelled) return;
        setJob(data);
        if (data.status === "done") {
          setAnalysis(data);
          setPhase("done");
          if (data.job_id && !String(data.job_id).startsWith("demo")) {
            const entry = entryFor(data);
            setSaved((current) => {
              const next = [entry, ...current.filter((item) => item.job_id !== entry.job_id)].slice(
                0,
                MAX_SAVED
              );
              writeSaved(next);
              return next;
            });
          }
          return;
        }
        if (data.status === "error") {
          setError(data.error?.message || "The analysis failed.");
          setPhase("error");
          return;
        }
        timer = window.setTimeout(poll, 1500);
      } catch (pollError) {
        if (!cancelled) {
          setError(pollError.message || "Could not reach the API.");
          setPhase("error");
        }
      }
    }

    poll();
    return () => {
      cancelled = true;
      if (timer) window.clearTimeout(timer);
    };
  }, [phase, jobId]);

  async function startUpload(file) {
    const problem = validateFile(file);
    if (problem) {
      setError(problem);
      setPhase("error");
      return;
    }
    setError("");
    setAnalysis(null);
    setJobId(null);
    setJob({ filename: file.name, status: "queued", progress: 0, stage: "Uploading" });
    setPhase("working");
    setChatOpen(false);
    try {
      const created = await uploadPaper(file);
      setJob({ ...created, filename: file.name, progress: 2, stage: "Queued" });
      setJobId(created.job_id);
    } catch (uploadError) {
      setError(uploadError.message || "The upload failed.");
      setPhase("error");
    }
  }

  function reset() {
    setPhase("start");
    setAnalysis(null);
    setJob(null);
    setJobId(null);
    setError("");
    setTab("summary");
    setChatOpen(false);
  }

  const isDemo = !analysis?.job_id || String(analysis.job_id).startsWith("demo");
  const canCompare = Boolean(analysis) && (isDemo || saved.length >= 2);
  const chatEnabled = Boolean(analysis) && !isDemo && config?.gemini_enabled !== false;

  if (phase === "start") {
    return <StartScreen onFile={startUpload} onDemo={() => {
      setAnalysis(MOCK_ANALYSIS);
      setJob(null);
      setJobId(null);
      setTab("summary");
      setPhase("done");
    }} busy={false} />;
  }

  if (phase === "working") {
    return <ProgressScreen job={job} uploading={!jobId} />;
  }

  if (phase === "error") {
    return <ErrorScreen message={error} onReset={reset} />;
  }

  if (phase === "portfolio") {
    return <PortfolioScreen saved={saved} demo={isDemo} onBack={() => setPhase("done")} />;
  }

  if (!analysis) {
    return <StartScreen onFile={startUpload} onDemo={reset} busy={false} />;
  }

  return (
    <>
      <Analysis
        analysis={analysis}
        tab={tab}
        setTab={setTab}
        isDemo={isDemo}
        canCompare={canCompare}
        chatEnabled={chatEnabled}
        onChat={() => setChatOpen(true)}
        onCompare={() => setPhase("portfolio")}
        onReset={reset}
      />
      <ChatSheet
        open={chatOpen}
        onClose={() => setChatOpen(false)}
        analysis={analysis}
        geminiEnabled={config?.gemini_enabled}
        chat={chat}
      />
    </>
  );
}
