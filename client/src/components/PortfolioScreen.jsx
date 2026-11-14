import { useState } from "react";
import MOCK_PORTFOLIO from "../mocks/portfolio.json";
import { createPortfolio } from "../api.js";
import { EmptyState, Icon, LevelScale, formatPercent } from "./ui.jsx";

const STANCES = {
  conflict: { label: "Disagree", tone: "insufficient" },
  agree: { label: "Agree", tone: "supported" },
  insufficient: { label: "Unclear", tone: "partial" },
  unscored: { label: "Not scored", tone: "neutral" },
};

function Scores({ entry }) {
  const nli = entry.nli || {};
  if (!nli.forward && !nli.backward) return null;
  return (
    <details className="ledger-scores">
      <summary>Model scores</summary>
      <dl>
        <div>
          <dt>First → second</dt>
          <dd>
            entailment {formatPercent(nli.forward?.entailment)} · contradiction{" "}
            {formatPercent(nli.forward?.contradiction)}
          </dd>
        </div>
        <div>
          <dt>Second → first</dt>
          <dd>
            entailment {formatPercent(nli.backward?.entailment)} · contradiction{" "}
            {formatPercent(nli.backward?.contradiction)}
          </dd>
        </div>
      </dl>
    </details>
  );
}

function PaperSummary({ paper }) {
  const trl = paper.trl?.level;
  const repro = paper.reproducibility?.score;
  return (
    <div className="pick-main">
      <span className="pick-title">{paper.title}</span>
      <span className="pick-meta">
        TRL {trl ?? "—"}/9 · reproducibility {repro ?? "—"}/100 ·{" "}
        {paper.claims?.supported ?? 0} of {paper.claims?.total ?? 0} claims supported
      </span>
    </div>
  );
}

export default function PortfolioScreen({ saved, demo, onBack }) {
  const [selection, setSelection] = useState(saved.slice(0, 3).map((item) => item.job_id));
  const [result, setResult] = useState(demo ? MOCK_PORTFOLIO : null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const isSample = result?.portfolio_id === "demo-portfolio";
  const canPick = saved.length >= 2;

  function toggle(jobId) {
    setSelection((current) => {
      if (current.includes(jobId)) return current.filter((item) => item !== jobId);
      if (current.length >= 5) return current;
      return [...current, jobId];
    });
  }

  async function compare() {
    if (selection.length < 2 || busy) return;
    setBusy(true);
    setError("");
    try {
      setResult(await createPortfolio(selection));
    } catch (compareError) {
      setError(compareError.message || "The comparison failed.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="portfolio">
      <header className="portfolio-head">
        <div>
          <p className="eyebrow">Portfolio{isSample ? " · sample" : ""}</p>
          <h1>Which of these is worth building?</h1>
          <p className="verdict-line">
            {result?.summary?.headline || "Pick two to five analyses to compare."}
          </p>
        </div>
        <button type="button" className="button quiet" onClick={onBack}>Back to paper</button>
      </header>

      {canPick ? (
        <section className="block">
          <div className="block-head">
            <h2>Papers</h2>
            <span className="muted">{selection.length} selected</span>
          </div>
          <div className="picker">
            {saved.map((item) => (
              <label className="pick" key={item.job_id}>
                <input
                  type="checkbox"
                  checked={selection.includes(item.job_id)}
                  onChange={() => toggle(item.job_id)}
                />
                <PaperSummary
                  paper={{
                    title: item.title,
                    trl: { level: item.trl },
                    reproducibility: { score: item.repro },
                    claims: { supported: item.supported, total: item.claims },
                  }}
                />
              </label>
            ))}
          </div>
          <div className="picker-actions">
            <button
              type="button"
              className="button"
              onClick={compare}
              disabled={selection.length < 2 || busy}
            >
              {busy ? "Comparing…" : `Compare ${selection.length} papers`}
            </button>
            <span className="muted">Up to five. Nothing is merged into one document.</span>
          </div>
        </section>
      ) : null}

      {error ? <p className="error-line">{error}</p> : null}

      {result ? (
        <>
          <section className="portfolio-stats" aria-label="Portfolio summary">
            <div className="portfolio-stat">
              <span>Papers compared</span>
              <strong>{result.summary.papers}</strong>
            </div>
            <div className="portfolio-stat">
              <span>Shared claims</span>
              <strong>{result.summary.shared}</strong>
            </div>
            <div className={`portfolio-stat ${result.summary.conflicts ? "is-alert" : ""}`}>
              <span>Disagreements</span>
              <strong>{result.summary.conflicts}</strong>
            </div>
          </section>

          <section className="block">
            <div className="block-head">
              <h2>Readiness</h2>
              <span className="muted">
                {result.summary.papers} papers · {result.summary.claims} claims
              </span>
            </div>
            <div className="table-wrap">
              <table className="compare">
                <thead>
                  <tr>
                    <th scope="col">Paper</th>
                    <th scope="col">TRL</th>
                    <th scope="col">Rebuild</th>
                    <th scope="col">Supported</th>
                    <th scope="col">Ships</th>
                  </tr>
                </thead>
                <tbody>
                  {result.papers.map((paper) => (
                    <tr key={paper.job_id}>
                      <td>
                        <strong>{paper.title}</strong>
                        <span className="row-sub">{paper.pages} pages</span>
                      </td>
                      <td data-label="TRL">
                        <span className="metric-cell">
                          <span>{paper.trl?.level ?? "—"}/9</span>
                          <LevelScale level={paper.trl?.level} />
                        </span>
                      </td>
                      <td data-label="Rebuild">{paper.reproducibility?.score ?? "—"}/100</td>
                      <td data-label="Claims supported">
                        {paper.claims?.supported ?? 0}/{paper.claims?.total ?? 0}
                      </td>
                      <td data-label="Ships">
                        {paper.artifacts?.available?.length
                          ? `${paper.artifacts.available.length} shipped`
                          : "Nothing"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>

          <section className="block">
            <div className="block-head">
              <h2>Shared claims</h2>
              <span className="muted">
                {result.ledger.length} matched
                {result.summary.nli_model ? ` · ${result.summary.nli_model}` : ""}
              </span>
            </div>
            {result.ledger.length ? (
              <div className="ledger">
                {result.ledger.map((entry, index) => {
                  const stance = STANCES[entry.stance] || STANCES.unscored;
                  return (
                    <article className="ledger-row" key={`${entry.a.claim_id}-${entry.b.claim_id}-${index}`}>
                      <div className="ledger-head">
                        <span className={`stance stance-${stance.tone}`}>{stance.label}</span>
                        <span className="muted">
                          {formatPercent(entry.similarity)} claim overlap
                        </span>
                      </div>
                      <div className="ledger-claims">
                        <div>
                          <span className="paper-tag">
                            {entry.a.title} · p.{entry.a.page}
                          </span>
                          <p>{entry.a.text}</p>
                        </div>
                        <div>
                          <span className="paper-tag">
                            {entry.b.title} · p.{entry.b.page}
                          </span>
                          <p>{entry.b.text}</p>
                        </div>
                      </div>
                      <Scores entry={entry} />
                    </article>
                  );
                })}
              </div>
            ) : (
              <EmptyState title="No shared claims">
                These papers do not make the same claim in similar words.
              </EmptyState>
            )}
          </section>
        </>
      ) : (
        <EmptyState title="Nothing to compare yet">
          Analyse a second paper, then pick two or more here.
        </EmptyState>
      )}

      <p className="muted portfolio-foot">
        <Icon name="portfolio" size={14} /> This compares readiness and shared claims. It does
        not answer questions across the papers.
      </p>
    </main>
  );
}
