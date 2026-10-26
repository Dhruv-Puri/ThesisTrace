import { EmptyState, TYPE_LABELS } from "../components/ui.jsx";

const TYPE_ORDER = [
  "DATASET",
  "MODEL",
  "ALGORITHM",
  "METRIC",
  "PER",
  "ORG",
  "LOC",
  "HARDWARE",
  "TECH",
];

const GROUP_META = {
  models: { title: "Models & methods", note: "Architectures and algorithms named in the paper." },
  datasets: { title: "Datasets & benchmarks", note: "Data the results are measured on." },
  metrics: { title: "Metrics", note: "What the authors use to claim success." },
  others: { title: "People & organisations", note: "Named authors, labs and institutions." },
};

export default function ConceptsTab({ analysis }) {
  const entities = analysis?.entities || [];
  const concepts = analysis?.key_concepts || { models: [], datasets: [], metrics: [], others: [] };

  const grouped = entities.reduce((accumulator, entity) => {
    const type = entity.type || "TECH";
    if (!accumulator[type]) accumulator[type] = [];
    accumulator[type].push(entity);
    return accumulator;
  }, {});

  const types = TYPE_ORDER.filter((type) => grouped[type]?.length).concat(
    Object.keys(grouped).filter((type) => !TYPE_ORDER.includes(type))
  );

  return (
    <div className="tab-stack">
      <section className="panel">
        <div className="panel-head">
          <div>
            <p className="kicker">Practical 2 · Hugging Face NER + gazetteer</p>
            <h2>Key concepts, with pages</h2>
          </div>
        </div>
        <p className="panel-lede">
          A DistilBERT CoNLL model finds people, organisations and locations; a curated
          scientific gazetteer adds datasets, metrics, models and algorithms. When both
          recognise the same span, the model keeps the boundaries and the gazetteer supplies
          the type. Every chip is a mention, not a guess.
        </p>
        {entities.length ? (
          <div className="entity-groups">
            {types.map((type) => (
              <div className="entity-group" key={type}>
                <h3>
                  {TYPE_LABELS[type] || type}
                  <span>{grouped[type].length}</span>
                </h3>
                <div className="chips">
                  {grouped[type].map((entity, index) => (
                    <span
                      className={`chip chip-${String(type).toLowerCase()}`}
                      key={`${entity.text}-${entity.page}-${index}`}
                      title={`${entity.source || "extracted"} · page ${entity.page}`}
                    >
                      {entity.text}
                      <span className="chip-page">p.{entity.page}</span>
                    </span>
                  ))}
                </div>
              </div>
            ))}
          </div>
        ) : (
          <EmptyState title="No entities extracted">
            The document may be too short, or the NER model and gazetteer found no named
            concepts. Try a full research paper.
          </EmptyState>
        )}
      </section>

      <div className="concept-columns">
        {Object.entries(GROUP_META).map(([key, meta]) => {
          const items = concepts[key] || [];
          return (
            <section className="panel concept-card" key={key}>
              <div className="panel-head">
                <div>
                  <p className="kicker">{meta.note}</p>
                  <h2>{meta.title}</h2>
                </div>
                <span className="count-badge">{items.length}</span>
              </div>
              {items.length ? (
                <ul className="concept-list">
                  {items.map((item) => (
                    <li key={`${key}-${item.name}`}>
                      <div>
                        <strong>{item.name}</strong>
                        <span className="concept-type">{item.type}</span>
                      </div>
                      <span className="concept-count">
                        {item.count}× · p.{item.pages?.[0] ?? "?"}
                      </span>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="fine-print">Nothing in this group.</p>
              )}
            </section>
          );
        })}
      </div>

      <p className="syllabus-note">
        <span>CSR322 link</span> Named Entity Recognition and information extraction
        (Applications and Building Models), word classes, and Practical 2.
      </p>
    </div>
  );
}
