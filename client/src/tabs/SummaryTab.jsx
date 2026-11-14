import { useMemo } from "react";
import { CoverageRadar, EmptyState, RingGauge, TYPE_LABELS, formatNumber } from "../components/ui.jsx";
import LensPanel from "../components/LensPanel.jsx";

const PART_LABELS = {
  term_density: "Technical terms",
  sentence_length: "Sentence length",
  pos_mix: "Grammar mix",
  references: "References",
  structure: "Structure",
  lexical_variety: "Vocabulary",
};

function conceptList(analysis) {
  const groups = analysis?.key_concepts || {};
  const seen = new Set();
  const items = [];

  for (const group of ["datasets", "models", "metrics", "others"]) {
    for (const item of groups[group] || []) {
      const name = String(item?.name || "").trim();
      if (!name || seen.has(name.toLowerCase())) continue;
      seen.add(name.toLowerCase());
      items.push({
        name,
        type: item?.type || (group === "datasets" ? "DATASET" : group === "metrics" ? "METRIC" : "TECH"),
        page: item?.pages?.[0] ?? null,
      });
    }
  }

  if (!items.length) {
    for (const entity of analysis?.entities || []) {
      const name = String(entity?.text || "").trim();
      if (!name || seen.has(name.toLowerCase())) continue;
      seen.add(name.toLowerCase());
      items.push({ name, type: entity.type || "TECH", page: entity.page ?? null });
    }
  }

  return items.slice(0, 24);
}

export default function SummaryTab({ analysis }) {
  const summary = analysis?.summary || {};
  const bullets = summary.bullets || [];
  const concepts = useMemo(() => conceptList(analysis), [analysis]);
  const stats = analysis?.stats || {};
  const claims = analysis?.claims || [];
  const supported = claims.filter((claim) => claim.verdict === "supported").length;
  const trl = Number(analysis?.trl?.level);
  const repro = Number(analysis?.reproducibility?.score);

  const radarData = useMemo(
    () =>
      Object.entries(stats.complexity_parts || {})
        .map(([key, value]) => ({
          label: PART_LABELS[key] || key,
          value: Number(value) || 0,
        }))
        .filter((item) => item.value > 0),
    [stats.complexity_parts]
  );

  return (
    <div className="stack">
      <section className="glance" aria-label="Readiness at a glance">
        <div className="glance-cell">
          <RingGauge
            value={supported}
            max={claims.length || 1}
            display={`${supported}/${claims.length}`}
            label="Claims supported"
            tone="supported"
            size={88}
          />
        </div>
        <div className="glance-cell">
          <RingGauge
            value={trl}
            max={9}
            display={Number.isFinite(trl) ? trl : "—"}
            sublabel="/9"
            label="Readiness"
            tone="accent"
            size={88}
          />
        </div>
        <div className="glance-cell">
          <RingGauge
            value={repro}
            max={100}
            display={Number.isFinite(repro) ? repro : "—"}
            sublabel="/100"
            label="Reproducibility"
            tone={repro >= 70 ? "supported" : "gold"}
            size={88}
          />
        </div>
      </section>

      <LensPanel analysis={analysis} />

      <div className="summary-grid">
        <section className="block">
          <h2>Paper in three bullets</h2>
          {bullets.length ? (
            <ol className="bullets">
              {bullets.map((bullet, index) => (
                <li key={`bullet-${index}`}>
                  <span className="bullet-index" aria-hidden="true">{index + 1}</span>
                  <span>{bullet}</span>
                </li>
              ))}
            </ol>
          ) : (
            <EmptyState title="No summary produced">
              The document was too short or too damaged to summarise.
            </EmptyState>
          )}

          {summary.eli5 ? (
            <details className="disclosure">
              <summary>Explain it simply</summary>
              <p>{summary.eli5}</p>
            </details>
          ) : null}
        </section>

        {radarData.length ? (
          <section className="block profile">
            <div className="block-head">
              <h2>Content coverage</h2>
              <span className="muted">0–10</span>
            </div>
            <div className="radar-wrap">
              <CoverageRadar data={radarData} />
            </div>
            <p className="caption">Six measured dimensions, not a quality score.</p>
            <dl className="fact-row">
              <div><dt>Words</dt><dd>{formatNumber(stats.words)}</dd></div>
              <div><dt>Sections</dt><dd>{stats.sections ?? "—"}</dd></div>
              <div><dt>References</dt><dd>{stats.references ?? "—"}</dd></div>
              <div><dt>Reading</dt><dd>{stats.reading_minutes ?? "—"} min</dd></div>
            </dl>
          </section>
        ) : null}
      </div>

      <section className="block">
        <details className="disclosure concepts">
          <summary>
            <span>Key concepts</span>
            <span className="count">{concepts.length}</span>
          </summary>
          {concepts.length ? (
            <div className="chips">
              {concepts.map((concept) => (
                <span className="chip" key={`${concept.name}-${concept.page}`}>
                  <span className="chip-type">{TYPE_LABELS[concept.type] || concept.type}</span>
                  {concept.name}
                  {concept.page ? <span className="chip-page">p.{concept.page}</span> : null}
                </span>
              ))}
            </div>
          ) : (
            <p className="muted">No datasets, models or metrics were recognised.</p>
          )}
        </details>
      </section>
    </div>
  );
}
