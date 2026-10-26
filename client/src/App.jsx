import { useEffect, useRef, useState } from "react";
import MOCK_ANALYSIS from "./mocks/paperAnalysis.json";
import { getConfig, getJob, uploadPaper } from "./api.js";
import ClaimCheckTab from "./tabs/ClaimCheckTab.jsx";
import ConceptsTab from "./tabs/ConceptsTab.jsx";
import OverviewTab from "./tabs/OverviewTab.jsx";
import ReportTab from "./tabs/ReportTab.jsx";
import ReproTab from "./tabs/ReproTab.jsx";
import TRLTab from "./tabs/TRLTab.jsx";
import { formatNumber } from "./components/ui.jsx";

const MAX_MB = 30;
const ALLOWED = ["pdf", "txt", "md"];
const TABS = [
  { id: "overview", label: "Overview" },
  { id: "concepts", label: "Key concepts" },
  { id: "claims", label: "ClaimCheck" },
  { id: "repro", label: "Reproducibility" },
  { id: "trl", label: "TRL" },
  { id: "report", label: "Report" },
];

function validateFile(file) {
  const extension = file.name.split(".").pop()?.toLowerCase() || "";
  if (!ALLOWED.includes(extension)) return "Upload a PDF, .txt or .md file.";
  if (file.size === 0) return "That file is empty.";
  if (file.size > MAX_MB * 1024 * 1024) return `Maximum upload size is ${MAX_MB} MB.`;
  return "";
}

function Dropzone({ onFile, busy }) {
  const [dragging, setDragging] = useState(false);
  const inputRef = useRef(null);

  function handleDrop(event) {
    event.preventDefault();
    setDragging(false);
    const file = event.dataTransfer.files?.[0];
    if (file && !busy) onFile(file);
  }

  return (
    <label
      className={`dropzone ${dragging ? "is-dragging" : ""} ${busy ? "is-busy" : ""}`}
      htmlFor="paper-upload"
      onDragOver={(event) => {
        event.preventDefault();
        if (!busy) setDragging(true);
      }}
      onDragLeave={() => setDragging(false)}
      onDrop={handleDrop}
      aria-disabled={busy}
    >
      <input
        ref={inputRef}
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
      <span className="drop-icon" aria-hidden="true">↥</span>
      <span className="drop-copy">
        <strong>{busy ? "Uploading…" : "Drop a paper here"}</strong>
        <span>PDF or plain text · up to {MAX_MB} MB · processed locally</span>
      </span>
      <span className="button ghost">{busy ? "Working" : "Choose file"}</span>
    </label>
  );
}

function Landing({ onFile, onDemo, busy }) {
  return (
    <main className="landing">
      <section className="hero">
        <div className="hero-copy">
          <p className="eyebrow">CSR322 · Natural Language Processing</p>
          <h1>
            From paper
            <br />
            to <em>evidence</em>.
          </h1>
          <p className="lede">
            Upload a research paper. Paper2Reality explains what it does, extracts the key
            concepts, checks whether its claims survive its own evidence, scores technology
            readiness, and shows what still stands between the lab and the real world.
          </p>
          <Dropzone onFile={onFile} busy={busy} />
          <div className="demo-row">
            <button type="button" className="text-button" onClick={onDemo}>
              Or explore a demo analysis →
            </button>
            <span className="fine-print">no upload, no network</span>
          </div>
        </div>

        <aside className="hero-aside">
          <p className="aside-label">The pipeline</p>
          <ol className="pipeline-list">
            <li><span className="num">01</span><div><strong>Read</strong><small>PDF → pages → sections</small></div></li>
            <li><span className="num">02</span><div><strong>Tokenize</strong><small>BPE · WordPiece · SentencePiece</small></div></li>
            <li><span className="num">03</span><div><strong>Tag</strong><small>POS, NER, scientific gazetteer</small></div></li>
            <li><span className="num">04</span><div><strong>Summarize</strong><small>3 bullets + a beginner explanation</small></div></li>
            <li><span className="num">05</span><div><strong>Verify</strong><small>retrieve passages → NLI verdict</small></div></li>
            <li><span className="num">06</span><div><strong>Assess</strong><small>reproducibility → TRL → report</small></div></li>
          </ol>
          <p className="aside-foot">
            Classical NLP first. Neural models second. The LLM is optional and never decides a
            verdict.
          </p>
        </aside>
      </section>

      <section className="capabilities">
        <article>
          <span className="cap-index">01</span>
          <h2>Grounded claims</h2>
          <p>Every verdict points to the exact sentence and page it came from. Unsupported is a valid answer.</p>
        </article>
        <article>
          <span className="cap-index">02</span>
          <h2>Readiness, not hype</h2>
          <p>A deterministic TRL rubric over the paper’s own wording, with the evidence quoted beside each level.</p>
        </article>
        <article>
          <span className="cap-index">03</span>
          <h2>Reproducibility gaps</h2>
          <p>Twelve concrete signals — dataset, code, seed, hyperparameters, baseline — not a vague “quality” score.</p>
        </article>
      </section>

      <p className="landing-foot">
        Built for the CSR322 syllabus: tokenization, POS, TF-IDF, NER, summarization,
        classification, RAG, prompt engineering and evaluation — in one working pipeline.
      </p>
    </main>
  );
}

function ProgressView({ job, uploading }) {
  const progress = Math.max(uploading ? 2 : 0, Number(job?.progress) || 0);
  const stage = job?.stage || (uploading ? "Uploading file" : "Queued");
  return (
    <main className="center-page">
      <section className="progress-card" aria-live="polite">
        <p className="eyebrow">Reading the paper</p>
        <h1>{uploading ? "Uploading" : "Analysing"}</h1>
        <p className="progress-file">{job?.filename || "your document"}</p>
        <div className="progress-track" role="progressbar" aria-valuenow={progress} aria-valuemin={0} aria-valuemax={100}>
          <div className="progress-fill" style={{ width: `${Math.max(progress, 2)}%` }} />
        </div>
        <div className="progress-meta">
          <span>{stage}</span>
          <span>{progress}%</span>
        </div>
        <div className="progress-steps">
          <span>Retrieval</span>
          <span>NLI</span>
          <span>TRL</span>
          <span>Report</span>
        </div>
        <p className="fine-print">
          A CPU analysis takes roughly 15–45 seconds. The browser polls every 1.5 seconds, so
          you can close this tab and the job keeps running in the container.
        </p>
      </section>
    </main>
  );
}

function Warnings({ warnings }) {
  if (!warnings?.length) return null;
  return (
    <details className="notes">
      <summary>
        {warnings.length} pipeline note{warnings.length === 1 ? "" : "s"} · model fallbacks,
        quota, or safety
      </summary>
      <ul>
        {warnings.map((warning, index) => (
          <li key={`warning-${index}`}>{warning}</li>
        ))}
      </ul>
    </details>
  );
}

function Dashboard({ analysis, onReset }) {
  const [tab, setTab] = useState("overview");
  const claims = analysis.claims || [];
  const supported = claims.filter((claim) => claim.verdict === "supported").length;
  const partial = claims.filter((claim) => claim.verdict === "partially_supported").length;
  const trl = analysis.trl || {};
  const repro = analysis.reproducibility || {};
  const entities = analysis.entities || [];
  const stats = analysis.stats || {};
  const warnings = analysis.warnings || [];
  const isDemo = !analysis.job_id || String(analysis.job_id).startsWith("demo");

  const badges = {
    concepts: entities.length,
    claims: claims.length,
    repro: repro.score,
    trl: trl.level,
  };

  return (
    <main className="dashboard">
      <section className="paper-head">
        <div>
          <p className="eyebrow">
            {isDemo ? "Demo analysis" : "Analysis complete"} · {analysis.doc?.pages || 0} pages
          </p>
          <h1>{analysis.doc?.title || "Untitled paper"}</h1>
          <p className="paper-meta">
            {analysis.doc?.filename || "document"} · {formatNumber(analysis.doc?.words || stats.words)} words
            · about {stats.reading_minutes || 0} min read
          </p>
        </div>
        <div className="paper-actions">
          <button type="button" className="button secondary" onClick={onReset}>
            New analysis
          </button>
        </div>
      </section>

      <section className="score-strip" aria-label="Key results">
        <div className="mini-card">
          <span className="mini-label">Claims supported</span>
          <strong>{supported}<small> / {claims.length}</small></strong>
          <span className="mini-detail">{partial} partial · {claims.length - supported - partial} insufficient</span>
        </div>
        <div className="mini-card">
          <span className="mini-label">Technology readiness</span>
          <strong>TRL {trl.level ?? "—"}<small>/9</small></strong>
          <span className="mini-detail">{trl.label || "not assessed"}</span>
        </div>
        <div className="mini-card">
          <span className="mini-label">Reproducibility</span>
          <strong>{repro.score ?? "—"}<small>/100</small></strong>
          <span className="mini-detail">{repro.summary || "no audit"}</span>
        </div>
        <div className="mini-card">
          <span className="mini-label">Entities extracted</span>
          <strong>{entities.length}</strong>
          <span className="mini-detail">{Object.keys(analysis.key_concepts || {}).length} concept groups</span>
        </div>
      </section>

      <Warnings warnings={warnings} />

      <nav className="tabs" aria-label="Analysis sections">
        {TABS.map((item) => (
          <button
            key={item.id}
            type="button"
            className={`tab ${tab === item.id ? "active" : ""}`}
            onClick={() => setTab(item.id)}
            aria-selected={tab === item.id}
          >
            {item.label}
            {badges[item.id] !== undefined && badges[item.id] !== null ? (
              <span className="tab-count">{badges[item.id]}</span>
            ) : null}
          </button>
        ))}
      </nav>

      <div className="tab-panel">
        {tab === "overview" ? <OverviewTab analysis={analysis} /> : null}
        {tab === "concepts" ? <ConceptsTab analysis={analysis} /> : null}
        {tab === "claims" ? <ClaimCheckTab analysis={analysis} /> : null}
        {tab === "repro" ? <ReproTab analysis={analysis} /> : null}
        {tab === "trl" ? <TRLTab analysis={analysis} /> : null}
        {tab === "report" ? <ReportTab analysis={analysis} /> : null}
      </div>

      <footer className="dashboard-foot">
        <span>Paper2Reality · CSR322</span>
        <span>pipeline {analysis.pipeline_version || "—"} · {analysis.engine?.tfidf || "TF-IDF"} · {analysis.engine?.gemini ? "Gemini optional" : "fully local"}</span>
      </footer>
    </main>
  );
}

export default function App() {
  const [phase, setPhase] = useState("idle");
  const [jobId, setJobId] = useState(null);
  const [job, setJob] = useState(null);
  const [analysis, setAnalysis] = useState(null);
  const [error, setError] = useState("");
  const [config, setConfig] = useState(null);
  const [isDemo, setIsDemo] = useState(false);

  useEffect(() => {
    getConfig().then(setConfig).catch(() => setConfig(null));
  }, []);

  useEffect(() => {
    if (!jobId || isDemo) return undefined;
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
  }, [jobId, isDemo]);

  async function startUpload(file) {
    const problem = validateFile(file);
    if (problem) {
      setError(problem);
      setPhase("error");
      return;
    }
    setError("");
    setIsDemo(false);
    setJob({ filename: file.name, stage: "Uploading file", progress: 2, status: "queued" });
    setPhase("uploading");
    try {
      const created = await uploadPaper(file);
      setJobId(created.job_id);
      setJob({
        filename: created.filename || file.name,
        stage: "Queued",
        progress: 2,
        status: "queued",
      });
      setPhase("running");
    } catch (uploadError) {
      setError(uploadError.message || "The upload failed.");
      setPhase("error");
    }
  }

  function startDemo() {
    setAnalysis({ ...MOCK_ANALYSIS });
    setIsDemo(true);
    setJob(null);
    setJobId(null);
    setError("");
    setPhase("done");
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  function reset() {
    setPhase("idle");
    setJob(null);
    setJobId(null);
    setAnalysis(null);
    setError("");
    setIsDemo(false);
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  return (
    <div className="app">
      <header className="topbar">
        <button type="button" className="wordmark" onClick={reset} aria-label="Paper2Reality home">
          Paper<span className="wordmark-arrow">→</span>Reality
        </button>
        <div className="topbar-right">
          {config ? (
            <span className={`mode ${config.gemini_enabled ? "mode-gemini" : ""}`}>
              {config.gemini_enabled ? "Gemini optional" : "fully local"}
            </span>
          ) : null}
          <span className="course">CSR322 · NLP</span>
        </div>
      </header>

      {phase === "idle" ? (
        <Landing onFile={startUpload} onDemo={startDemo} busy={false} />
      ) : null}

      {phase === "uploading" || phase === "running" ? (
        <ProgressView job={job} uploading={phase === "uploading"} />
      ) : null}

      {phase === "error" ? (
        <main className="center-page">
          <section className="error-card">
            <span className="error-mark" aria-hidden="true">!</span>
            <p className="eyebrow">Could not analyse this document</p>
            <h1>That one did not work.</h1>
            <p>{error}</p>
            <div className="button-row">
              <button type="button" className="button primary" onClick={reset}>
                Try another paper
              </button>
              <button type="button" className="button secondary" onClick={startDemo}>
                Explore the demo
              </button>
            </div>
          </section>
        </main>
      ) : null}

      {phase === "done" && analysis ? (
        <Dashboard analysis={analysis} onReset={reset} />
      ) : null}

      <footer className="site-footer">
        <span>Paper2Reality · research-to-commercialization intelligence</span>
        <span>CSR322 project · local-first · ₹0 to run</span>
      </footer>
    </div>
  );
}
