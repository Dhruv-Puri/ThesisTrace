import { EmptyState, Tag } from "../components/ui.jsx";

const LABELS = {
  1: "Basic principles observed",
  2: "Technology concept formulated",
  3: "Experimental proof of concept",
  4: "Technology validated in lab",
  5: "Technology validated in relevant environment",
  6: "Technology demonstrated in relevant environment",
  7: "System prototype demonstrated in operational environment",
  8: "System complete and qualified",
  9: "Actual system proven in operational environment",
};

const SIGNAL_LABELS = {
  problem: "Problem stated",
  method: "Method described",
  experiment: "Experiment",
  baseline: "Baseline",
  relevant: "Relevant environment",
  field: "Field / pilot",
  operational: "Operational",
  certified: "Certified",
  proven: "Proven in operation",
};

export default function TRLTab({ analysis }) {
  const trl = analysis?.trl;
  if (!trl) {
    return <EmptyState title="No TRL assessment">The readiness rubric did not run.</EmptyState>;
  }
  const level = Number(trl.level) || 1;
  const evidence = trl.evidence || [];

  return (
    <div className="tab-stack">
      <section className="trl-hero">
        <div className="trl-current">
          <p className="kicker">Technology readiness · deterministic rubric</p>
          <p className="trl-number">TRL {level}<span>/9</span></p>
          <h2>{trl.label || LABELS[level]}</h2>
          <p className="panel-lede">{trl.why}</p>
          <div className="trl-tags">
            <Tag tone="accent">{evidence.length} cited signals</Tag>
            {trl.review_document ? <Tag tone="warn">review document</Tag> : null}
            <Tag tone="neutral">{trl.note}</Tag>
          </div>
        </div>
        <div className="trl-ladder" aria-label="TRL ladder">
          {Array.from({ length: 9 }, (_, index) => 9 - index).map((value) => (
            <div
              className={`trl-rung ${value < level ? "reached" : ""} ${value === level ? "current" : ""}`}
              key={value}
            >
              <span className="rung-level">TRL {value}</span>
              <span className="rung-label">{LABELS[value]}</span>
              <span className="rung-mark">
                {value === level ? "current" : value < level ? "evidenced" : "not evidenced"}
              </span>
            </div>
          ))}
        </div>
      </section>

      <div className="grid-2">
        <section className="panel">
          <div className="panel-head">
            <div>
              <p className="kicker">What the paper says</p>
              <h2>Evidence behind the level</h2>
            </div>
          </div>
          {evidence.length ? (
            <ul className="evidence-list">
              {evidence.map((item, index) => (
                <li key={`${item.signal}-${index}`}>
                  <div className="evidence-list-top">
                    <strong>{SIGNAL_LABELS[item.signal] || item.signal}</strong>
                    <span className="cite">[p.{item.page}]</span>
                    <span className="fine-print">level {item.level}</span>
                  </div>
                  {item.quote ? <p>“{item.quote}”</p> : null}
                </li>
              ))}
            </ul>
          ) : (
            <p className="fine-print">No positive TRL signal passed the text checks.</p>
          )}
        </section>

        <section className="panel">
          <div className="panel-head">
            <div>
              <p className="kicker">Rubric signals</p>
              <h2>What was found — and what was not</h2>
            </div>
          </div>
          <div className="signal-flags">
            {Object.entries(trl.signals || {}).map(([key, value]) => (
              <div className={`signal-flag ${value ? "flag-on" : "flag-off"}`} key={key}>
                <span aria-hidden="true">{value ? "✓" : "—"}</span>
                {SIGNAL_LABELS[key] || key}
              </div>
            ))}
          </div>
          <p className="fine-print">
            A negated sentence (“no field trial was conducted”) is deliberately not counted
            as evidence. The rubric caps the level when a higher signal is missing.
          </p>
        </section>
      </div>

      <p className="syllabus-note">
        <span>CSR322 link</span> Semantic analysis and evidence-grounded generation: the rubric
        maps meaning-bearing phrases to a readiness scale, and every claim is tied to a page.
        This is the project’s differentiator beyond the syllabus’s core NLP tasks.
      </p>
    </div>
  );
}
