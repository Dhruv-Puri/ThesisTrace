import { EmptyState, ReproStatus, Tag } from "../components/ui.jsx";

export default function ReproTab({ analysis }) {
  const report = analysis?.reproducibility;
  if (!report) {
    return <EmptyState title="No reproducibility audit">The analysis did not return a checklist.</EmptyState>;
  }
  const items = report.items || [];
  const score = Number(report.score) || 0;
  const present = items.filter((item) => item.status === "yes").length;
  const partial = items.filter((item) => item.status === "partial").length;
  const missing = items.filter((item) => item.status === "no").length;

  return (
    <div className="tab-stack">
      <section className="panel repro-hero">
        <div
          className="score-ring"
          style={{ "--score": score }}
          role="img"
          aria-label={`Reproducibility score ${score} out of 100`}
        >
          <span>{score}<small>/100</small></span>
        </div>
        <div className="repro-hero-copy">
          <p className="kicker">Static text audit · no code executed</p>
          <h2>Can another team reproduce this?</h2>
          <p className="panel-lede">{report.summary}</p>
          <div className="repro-summary-row">
            <span className="summary-pill pill-good">{present} present</span>
            <span className="summary-pill pill-warn">{partial} partial</span>
            <span className="summary-pill pill-bad">{missing} missing</span>
          </div>
          <p className="fine-print">{report.note}</p>
        </div>
        <Tag tone={score >= 70 ? "accent" : score >= 45 ? "warn" : "danger"}>
          {score >= 70 ? "strong" : score >= 45 ? "needs work" : "weak"}
        </Tag>
      </section>

      <section className="panel">
        <div className="panel-head">
          <div>
            <p className="kicker">Twelve signals from the text</p>
            <h2>Checklist</h2>
          </div>
          <Tag tone="neutral">weighted score</Tag>
        </div>
        <div className="table-wrap">
          <table className="data-table repro-table">
            <thead>
              <tr>
                <th scope="col">Signal</th>
                <th scope="col">Status</th>
                <th scope="col">Weight</th>
                <th scope="col">Evidence found</th>
              </tr>
            </thead>
            <tbody>
              {items.map((item) => (
                <tr key={item.key || item.name} className={`row-${item.status}`}>
                  <td><strong>{item.name}</strong></td>
                  <td><ReproStatus status={item.status} /></td>
                  <td>{item.weight}</td>
                  <td className="evidence-cell">{item.evidence}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <div className="grid-2">
        <section className="panel">
          <h2>What this score means</h2>
          <p className="panel-lede">
            A present signal is a concrete statement or link in the extracted text. “Partial”
            means a mention without the detail needed to actually repeat the work. The score is
            deliberately conservative: a missing random seed or dataset link costs real points.
          </p>
        </section>
        <section className="panel">
          <h2>What we do not do</h2>
          <p className="panel-lede">
            We do not download or run the authors’ code, and we do not claim a result was
            reproduced. Automated sandboxed execution is future work in the project roadmap;
            this tab is a text-level audit with page citations.
          </p>
        </section>
      </div>

      <p className="syllabus-note">
        <span>CSR322 link</span> Evidence extraction, evaluation and error analysis
        (Practical 6): the audit doubles as a structured error analysis of what the paper
        omits.
      </p>
    </div>
  );
}
