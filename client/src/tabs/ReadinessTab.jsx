import { EmptyState, RingGauge, StatusMark, Tag, firstSentence } from "../components/ui.jsx";

const TRL_LABELS = {
  1: "Basic principles observed",
  2: "Technology concept formulated",
  3: "Experimental proof of concept",
  4: "Validated in the lab",
  5: "Validated in a relevant environment",
  6: "Demonstrated in a relevant environment",
  7: "Prototype in an operational environment",
  8: "System complete and qualified",
  9: "Proven in operation",
};

function clip(text, limit = 180) {
  const clean = String(text || "").replace(/\s+/g, " ").trim();
  return clean.length > limit ? `${clean.slice(0, limit - 1)}…` : clean;
}

export default function ReadinessTab({ analysis }) {
  const trl = analysis?.trl;
  const repro = analysis?.reproducibility;
  if (!trl && !repro) {
    return (
      <EmptyState title="No readiness assessment">
        The rubric did not run for this document.
      </EmptyState>
    );
  }

  const level = Number(trl?.level) || 1;
  const items = repro?.items || [];
  const gaps = items.filter((item) => item.status !== "yes");
  const present = items.filter((item) => item.status === "yes");
  const partial = items.filter((item) => item.status === "partial").length;
  const missing = items.filter((item) => item.status === "no").length;

  return (
    <div className="stack">
      {trl ? (
        <section className="readiness-hero">
          <div className="trl-gauge" style={{ "--fill": `${(level / 9) * 360}deg` }}>
            <div className="trl-number">
              <span>{level}</span>
              <small>/9</small>
            </div>
          </div>
          <div className="readiness-copy">
            <p className="eyebrow">Technology readiness</p>
            <h2>{trl.label || TRL_LABELS[level]}</h2>
            <p className="lede">{firstSentence(trl.why)}</p>
            <div className="meta-row">
              {trl.confidence ? <Tag tone={trl.confidence === "high" ? "accent" : "neutral"}>{trl.confidence} confidence</Tag> : null}
              {Array.isArray(trl.level_range) && trl.level_range[0] !== trl.level_range[1] ? (
                <Tag>plausible {trl.level_range[0]}–{trl.level_range[1]}</Tag>
              ) : null}
              {trl.review_document ? <Tag tone="warn">review document</Tag> : null}
            </div>
          </div>
        </section>
      ) : null}

      {trl ? (
        <section className="block">
          <h3>Where the paper stops</h3>
          <ol className="ladder">
            {Array.from({ length: 9 }, (_, index) => 9 - index).map((value) => (
              <li
                key={value}
                className={`rung ${value < level ? "is-reached" : ""} ${value === level ? "is-current" : ""}`}
              >
                <span className="rung-level">{value}</span>
                <span className="rung-label">{TRL_LABELS[value]}</span>
                <span className="rung-mark">
                  {value === level ? "here" : value < level ? "evidenced" : ""}
                </span>
              </li>
            ))}
          </ol>
          {trl.note ? <p className="muted">Next level: {trl.note}</p> : null}
        </section>
      ) : null}

      {repro ? (
        <>
          <section className="block">
            <div className="block-head">
              <h3>Can it be rebuilt?</h3>
              <RingGauge
                value={Number(repro.score) || 0}
                max={100}
                size={72}
                display={repro.score ?? "—"}
                sublabel="/100"
                tone={Number(repro.score) >= 70 ? "supported" : "gold"}
              />
            </div>
            <p className="muted">{repro.summary}</p>
            <div className="signal-band">
              <div className="signal-bar" aria-hidden="true">
                {present.length ? <span className="signal-yes" style={{ flexGrow: present.length }} /> : null}
                {partial ? <span className="signal-partial" style={{ flexGrow: partial }} /> : null}
                {missing ? <span className="signal-no" style={{ flexGrow: missing }} /> : null}
              </div>
              <p className="signal-legend">
                <span><i className="legend-dot dot-yes" />{present.length} present</span>
                <span><i className="legend-dot dot-partial" />{partial} partial</span>
                <span><i className="legend-dot dot-no" />{missing} missing</span>
              </p>
            </div>
            {gaps.length ? (
              <ul className="gaps">
                {gaps.map((item) => (
                  <li key={item.key || item.name}>
                    <div className="gap-head">
                      <strong>{item.name}</strong>
                      <StatusMark status={item.status} />
                    </div>
                    <p>{clip(item.evidence)}</p>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="muted">Every checked signal was present in the text.</p>
            )}
          </section>

          {present.length ? (
            <details className="disclosure block">
              <summary>
                <span>What the paper does provide</span>
                <span className="count">{present.length}</span>
              </summary>
              <ul className="present-list">
                {present.map((item) => (
                  <li key={item.key || item.name}>
                    <strong>{item.name}</strong>
                    <span>{clip(item.evidence, 140)}</span>
                  </li>
                ))}
              </ul>
            </details>
          ) : null}
        </>
      ) : null}
    </div>
  );
}
