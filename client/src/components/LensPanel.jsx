import { useState } from "react";

const LENSES = [
  { id: "researcher", label: "Researcher" },
  { id: "engineer", label: "Engineer" },
  { id: "business", label: "Business" },
];

const CALLS = {
  1: "Too early to build",
  2: "Concept stage — keep watching",
  3: "Proof of concept only",
  4: "Lab-validated — pilot next",
  5: "Ready for a relevant-environment pilot",
  6: "Ready for an operational demonstration",
  7: "Operational prototype — pilot with users",
  8: "Qualified system — deployment review",
  9: "Proven in operation",
};

const NEXT_STEPS = {
  1: "Define a testable prototype.",
  2: "Turn the concept into a lab experiment.",
  3: "Prove the core result in a controlled setting.",
  4: "Run a pilot in a relevant environment.",
  5: "Demonstrate the system with real data.",
  6: "Pilot with users and measure the outcome.",
  7: "Run an operational pilot with a partner.",
  8: "Complete a deployment and security review.",
  9: "Move to procurement and scale-up.",
};

function clip(text, limit = 96) {
  const clean = String(text || "").replace(/\s+/g, " ").trim();
  return clean.length > limit ? `${clean.slice(0, limit - 1)}…` : clean;
}

function pageOf(claim, fallback = 1) {
  return claim?.evidence?.[0]?.page ?? claim?.page ?? fallback;
}

function buildLenses(analysis) {
  const claims = analysis?.claims || [];
  const supported = claims.filter((claim) => claim.verdict === "supported");
  const partial = claims.filter((claim) => claim.verdict === "partially_supported");
  const unresolved = claims.filter((claim) => claim.verdict !== "supported");
  const strongest = supported[0] || partial[0];
  const weakest = unresolved.find((claim) => claim.verdict === "insufficient") || unresolved[0];

  const repro = analysis?.reproducibility || {};
  const items = repro.items || [];
  const gaps = items.filter((item) => item.status !== "yes");
  const missing = items.filter((item) => item.status === "no");
  const missingNames = missing.map((item) => item.name).filter(Boolean);

  const level = Math.min(9, Math.max(1, Number(analysis?.trl?.level) || 1));
  const confidence = analysis?.trl?.confidence;
  const next = NEXT_STEPS[level];
  const call = CALLS[level];
  const score = Number.isFinite(Number(repro.score)) ? Number(repro.score) : 0;

  const researcherBody = claims.length
    ? strongest
      ? `The strongest result is “${clip(strongest.text, 118)}” [p.${pageOf(strongest)}]. ${
          unresolved.length
            ? `${unresolved.length} claim${unresolved.length === 1 ? "" : "s"} remain unresolved; those are the useful research questions.`
            : "Every extracted claim cleared the evidence threshold."
        }`
      : "No extracted claim cleared the evidence threshold. Read this as an open paper, not a settled result."
    : "No result-like claims were extracted. The document may be a review, a position paper, or too short for this pipeline.";

  return [
    {
      id: "researcher",
      role: "Researcher lens",
      headline: claims.length
        ? `${supported.length} of ${claims.length} claims survived the paper's own evidence.`
        : "No result-like claims were extracted.",
      body: researcherBody,
      facts: [
        { label: "Strongest signal", value: strongest ? `${clip(strongest.text, 74)} [p.${pageOf(strongest)}]` : "None found" },
        { label: "Still open", value: weakest ? `${clip(weakest.text, 72)} [p.${weakest.page}]` : "No unresolved claims" },
        { label: "Next question", value: next },
      ],
    },
    {
      id: "engineer",
      role: "Engineer lens",
      headline: `${score}/100 documented for rebuild.`,
      body: items.length
        ? `The paper documents ${items.length - gaps.length} of ${items.length} signals. ${
            missingNames.length
              ? `Missing: ${missingNames.slice(0, 4).join(", ")}.`
              : "Every checked signal is present."
          } Readiness stops at TRL ${level}.`
        : "No reproducibility checklist was produced for this document.",
      facts: [
        { label: "Readiness", value: `TRL ${level}/9` },
        { label: "First task", value: missingNames[0] ? `Publish ${missingNames[0].toLowerCase()}` : "Re-run the pipeline on your own data" },
        { label: "Blocked by", value: analysis?.trl?.note || "No next-level evidence was found" },
      ],
    },
    {
      id: "business",
      role: "Business lens",
      headline: call,
      body: `Evidence: ${supported.length} of ${claims.length} claims supported. Readiness: TRL ${level}/9${
        confidence ? `, ${confidence} confidence` : ""
      }. ${next}`,
      facts: [
        { label: "Evidence", value: `${supported.length}/${claims.length} supported · ${unresolved.length} unresolved` },
        { label: "Rebuild", value: `${score}/100 · ${missing.length} signals missing` },
        { label: "Next milestone", value: next },
      ],
    },
  ];
}

export default function LensPanel({ analysis }) {
  const [active, setActive] = useState("researcher");
  const lenses = buildLenses(analysis);
  const index = Math.max(0, lenses.findIndex((lens) => lens.id === active));
  const lens = lenses[index] || lenses[0];

  return (
    <section className="lenses" aria-labelledby="lens-title">
      <div className="lens-head">
        <div>
          <p className="eyebrow">Decision lenses</p>
          <h2 id="lens-title">Same paper, three decisions.</h2>
        </div>
        <div
          className="lens-switch"
          role="tablist"
          aria-label="Choose a decision lens"
          onKeyDown={(event) => {
            if (event.key !== "ArrowRight" && event.key !== "ArrowLeft") return;
            event.preventDefault();
            const step = event.key === "ArrowRight" ? 1 : -1;
            const next = (index + step + lenses.length) % lenses.length;
            setActive(lenses[next].id);
            event.currentTarget.querySelectorAll('[role="tab"]')[next]?.focus();
          }}
        >
          <span
            className="lens-thumb"
            aria-hidden="true"
            style={{ transform: `translateX(${index * 100}%)` }}
          />
          {LENSES.map((item) => (
            <button
              key={item.id}
              type="button"
              role="tab"
              aria-selected={active === item.id}
              className={active === item.id ? "is-active" : ""}
              onClick={() => setActive(item.id)}
            >
              {item.label}
            </button>
          ))}
        </div>
      </div>

      <div className="lens-body" key={lens.id} aria-live="polite">
        <div className="lens-copy">
          <span className="lens-role">{lens.role}</span>
          <h3>{lens.headline}</h3>
          <p>{lens.body}</p>
        </div>
        <dl className="lens-facts">
          {lens.facts.map((fact) => (
            <div key={fact.label}>
              <dt>{fact.label}</dt>
              <dd>{fact.value}</dd>
            </div>
          ))}
        </dl>
      </div>
    </section>
  );
}
