import { useEffect, useState } from "react";
import { getBusinessIntelligence } from "../api.js";
import { EmptyState, Icon, Tag } from "../components/ui.jsx";
import TabHelperBanner from "../components/TabHelperBanner.jsx";

export default function BusinessIntelligenceTab({ analysis, isDemo }) {
  const jobId = analysis?.job_id;
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [activeFilter, setActiveFilter] = useState("all");

  const isDemoAnalysis = Boolean(
    isDemo || !jobId || String(jobId).startsWith("demo")
  );

  const fetchBI = async () => {
    if (isDemoAnalysis || !jobId) return;
    setLoading(true);
    setError(null);
    try {
      const response = await getBusinessIntelligence(jobId);
      setData(response);
    } catch (err) {
      setError(err?.message || "Failed to load business intelligence.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchBI();
  }, [jobId, isDemoAnalysis]);

  if (isDemoAnalysis) {
    return (
      <div className="tab-stack business-intelligence">
        <section className="intel-hero">
          <div className="intel-hero-copy">
            <span className="gap-eyebrow">COMMERCIAL TRANSLATION / BUSINESS INTELLIGENCE</span>
            <h2>How could this research create real-world value?</h2>
            <p>
              Evaluate real-world applications, target industries, commercial products, viable business models,
              and critical translational barriers grounded in research evidence.
            </p>
          </div>
        </section>

        <section className="intel-notice info">
          <div className="intel-notice-header">
            <Icon name="portfolio" size={18} />
            <strong>Real uploaded paper required</strong>
          </div>
          <p>
            Business Intelligence analyzes the actual technical contributions, empirical evidence, and technology readiness
            of an uploaded research paper. Demo mode uses precomputed mock data that cannot generate live commercial assessments.
            Upload your research paper from the start screen to explore commercial translation pathways.
          </p>
        </section>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="tab-stack business-intelligence">
        <section className="intel-hero">
          <div className="intel-hero-copy">
            <span className="gap-eyebrow">COMMERCIAL TRANSLATION / BUSINESS INTELLIGENCE</span>
            <h2>How could this research create real-world value?</h2>
            <p>Evaluating commercial potential and translational pathways...</p>
          </div>
        </section>

        <div className="intel-loading-card">
          <div className="intel-spinner" aria-hidden="true" />
          <div className="intel-loading-text">
            <h3>Analyzing commercial opportunities & translational pathways</h3>
            <p>
              Extracting the paper's technical profile, assessing readiness against empirical evidence,
              and synthesizing application areas, business models, and commercialization barriers.
            </p>
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="tab-stack business-intelligence">
        <section className="intel-hero">
          <div className="intel-hero-copy">
            <span className="gap-eyebrow">COMMERCIAL TRANSLATION / BUSINESS INTELLIGENCE</span>
            <h2>How could this research create real-world value?</h2>
          </div>
        </section>

        <div className="intel-error-card">
          <div className="intel-error-header">
            <Icon name="close" size={18} />
            <h3>Unable to evaluate business intelligence</h3>
          </div>
          <p>{error}</p>
          <button
            type="button"
            className="button"
            onClick={fetchBI}
            style={{ marginTop: "12px", alignSelf: "flex-start" }}
          >
            Retry analysis
          </button>
        </div>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="tab-stack business-intelligence">
        <EmptyState title="No business intelligence data available">
          Click below to initiate business intelligence and commercialization analysis.
        </EmptyState>
        <button
          type="button"
          className="button"
          onClick={fetchBI}
          style={{ margin: "16px auto 0", display: "block" }}
        >
          Run Business Intelligence
        </button>
      </div>
    );
  }

  const bi = data.business_intelligence || data;
  const overallAssessment = data.overall_assessment || bi.overall_assessment || "";
  const applicationAreas = data.application_areas || bi.application_areas || [];
  const targetIndustries = data.target_industries || bi.target_industries || [];
  const targetCustomers = data.target_customers || bi.target_customers || [];
  const productOpportunities = data.product_opportunities || bi.product_opportunities || [];
  const pathways = data.commercialization_pathways || bi.commercialization_pathways || [];
  const businessModels = data.business_models || bi.business_models || [];
  const barriers = data.commercialization_barriers || bi.commercialization_barriers || [];
  const validationSteps = data.validation_steps || bi.validation_steps || [];
  const evidenceAndAssumptions = data.evidence_and_assumptions || bi.evidence_and_assumptions || [];
  const warnings = data.warnings || bi.warnings || [];

  const trlLevel = analysis?.trl?.level;
  const reproScore = analysis?.reproducibility?.score;

  const filteredBarriers =
    activeFilter === "all"
      ? barriers
      : barriers.filter(
          (b) => (b.severity || "").toLowerCase() === activeFilter.toLowerCase()
        );

  return (
    <div className="tab-stack business-intelligence">
      <section className="intel-hero">
        <div className="intel-hero-copy">
          <span className="gap-eyebrow">COMMERCIAL TRANSLATION / BUSINESS INTELLIGENCE</span>
          <h2>How could this research create real-world value?</h2>
          <p>
            Analysis of commercial pathways, product opportunities, industry pain points, and technical barriers
            grounded in paper readiness and empirical findings.
          </p>
        </div>
        <div className="intel-hero-stats">
          <div className="intel-stat-badge">
            <strong>{productOpportunities.length}</strong>
            <span>opportunities</span>
          </div>
          <div className="intel-stat-badge">
            <strong>{barriers.length}</strong>
            <span>barriers mapped</span>
          </div>
        </div>
      </section>

      <TabHelperBanner
        emoji="💡"
        title="Quick Guide: How to use Business Intelligence"
        tips={[
          "Real-World Applications: Discover practical problem spaces and specific supported use cases for this research.",
          "Target Industries & Personas: Identify which enterprise sectors and specific user roles face these problems.",
          "Product Opportunities: Review tangible platform, API, tool, or embedded system configurations.",
          "Barriers & Mitigations: Use the High / Medium risk filter to prioritize technical and regulatory blockers.",
          "Validation Roadmap: Check the exact experiments and customer discovery needed before commercialization.",
          "Audit Table: Check the bottom table to see which claims are proven paper evidence vs. AI commercial hypotheses.",
        ]}
      />

      {/* Commercial & Factual Guardrails Notice */}
      <section className="intel-disclaimer commercial">
        <div className="intel-disclaimer-title">
          <Icon name="portfolio" size={16} />
          <strong>Commercial Analysis Notice & Assumptions</strong>
        </div>
        <p>
          This evaluation outlines potential industry translation opportunities and translational risks.
          It intentionally excludes fabricated market sizes, revenue forecasts, and unverified customer commitments.
          Commercial hypotheses require real-world validation through customer discovery and technical pilot testing.
        </p>
      </section>

      {/* Overall Assessment & Readiness Context */}
      <section className="intel-card intel-bi-summary">
        <div className="intel-card-header">
          <span className="intel-card-tag">EXECUTIVE TRANSLATION ASSESSMENT</span>
          <div className="intel-badge-group">
            {trlLevel !== undefined && (
              <Tag tone="accent">TRL {trlLevel}/9</Tag>
            )}
            {reproScore !== undefined && (
              <Tag tone={reproScore >= 70 ? "supported" : "warn"}>
                Repro {reproScore}/100
              </Tag>
            )}
          </div>
        </div>
        <h3>Translational Assessment</h3>
        <p className="intel-lead-text">{overallAssessment || "Assessment summary not provided."}</p>
      </section>

      {/* A. Real-world Applications */}
      <section className="intel-card">
        <div className="intel-card-header">
          <span className="intel-card-tag">APPLICATIONS</span>
          <Tag tone="accent">{applicationAreas.length} Domains</Tag>
        </div>
        <h3>Real-World Application Areas</h3>
        <p className="intel-card-desc">
          Domains where the proposed methodology solves practical problems supported by the research.
        </p>

        {applicationAreas.length ? (
          <div className="intel-grid-2">
            {applicationAreas.map((item, idx) => (
              <div key={`app-${idx}`} className="intel-subcard">
                <div className="intel-subcard-header">
                  <span className="subcard-idx">0{idx + 1}</span>
                  <h4>{item.area}</h4>
                </div>
                {item.description && <p className="subcard-body">{item.description}</p>}
                {item.practical_use_cases?.length > 0 && (
                  <div className="subcard-list-box">
                    <span className="subcard-label">PRACTICAL USE CASES</span>
                    <ul>
                      {item.practical_use_cases.map((uc, uIdx) => (
                        <li key={`uc-${uIdx}`}>{uc}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            ))}
          </div>
        ) : (
          <p className="intel-empty-note">No specific application areas mapped.</p>
        )}
      </section>

      {/* B. Industry and Target Users */}
      <div className="intel-grid-2">
        <section className="intel-card">
          <div className="intel-card-header">
            <span className="intel-card-tag">TARGET INDUSTRIES</span>
            <Tag tone="neutral">Industry Fit</Tag>
          </div>
          <h3>Relevant Industries</h3>
          <p className="intel-card-desc">
            Sectors with operational bottlenecks addressed by this research.
          </p>

          {targetIndustries.length ? (
            <div className="intel-item-stack">
              {targetIndustries.map((ind, idx) => (
                <div key={`ind-${idx}`} className="intel-list-item">
                  <div className="intel-item-head">
                    <strong>{ind.industry}</strong>
                  </div>
                  {ind.relevance && <p className="intel-item-sub">{ind.relevance}</p>}
                  {ind.pain_points?.length > 0 && (
                    <div className="intel-tag-pills">
                      {ind.pain_points.map((p, pIdx) => (
                        <span key={`p-${pIdx}`} className="pill-tag">
                          {p}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </div>
          ) : (
            <p className="intel-empty-note">No target industries mapped.</p>
          )}
        </section>

        <section className="intel-card">
          <div className="intel-card-header">
            <span className="intel-card-tag">TARGET USERS & CUSTOMERS</span>
            <Tag tone="neutral">Stakeholders</Tag>
          </div>
          <h3>Target Customers & Personas</h3>
          <p className="intel-card-desc">
            End-user personas and customer segments facing problems this research addresses.
          </p>

          {targetCustomers.length ? (
            <div className="intel-item-stack">
              {targetCustomers.map((cust, idx) => (
                <div key={`cust-${idx}`} className="intel-list-item">
                  <div className="intel-item-head">
                    <strong>{cust.segment}</strong>
                    {cust.user_type && <span className="meta-badge">{cust.user_type}</span>}
                  </div>
                  {cust.problem_faced && (
                    <p className="intel-item-sub">
                      <strong>Problem:</strong> {cust.problem_faced}
                    </p>
                  )}
                  {cust.value_driver && (
                    <p className="intel-item-sub value-driver">
                      <strong>Value Driver:</strong> {cust.value_driver}
                    </p>
                  )}
                </div>
              ))}
            </div>
          ) : (
            <p className="intel-empty-note">No target customers identified.</p>
          )}
        </section>
      </div>

      {/* C. Product and Service Opportunities */}
      <section className="intel-card">
        <div className="intel-card-header">
          <span className="intel-card-tag">PRODUCTIZATION</span>
          <Tag tone="supported">Offerings</Tag>
        </div>
        <h3>Product & Service Opportunities</h3>
        <p className="intel-card-desc">
          Potential software platforms, APIs, developer tools, embedded systems, or services.
        </p>

        {productOpportunities.length ? (
          <div className="intel-grid-2">
            {productOpportunities.map((prod, idx) => (
              <div key={`prod-${idx}`} className="intel-product-card">
                <div className="product-head">
                  <h4>{prod.name}</h4>
                  <Tag tone="accent">{prod.type || "Product"}</Tag>
                </div>
                {prod.value_proposition && (
                  <p className="product-value">{prod.value_proposition}</p>
                )}
                {prod.target_users && (
                  <p className="product-users">
                    <strong>Intended Users:</strong> {prod.target_users}
                  </p>
                )}
                {prod.technical_dependencies?.length > 0 && (
                  <div className="product-deps">
                    <strong>Technical Dependencies:</strong>
                    <ul>
                      {prod.technical_dependencies.map((dep, dIdx) => (
                        <li key={`dep-${dIdx}`}>{dep}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            ))}
          </div>
        ) : (
          <p className="intel-empty-note">No product opportunities identified.</p>
        )}
      </section>

      {/* D. Commercialization Pathways & Business Models */}
      <div className="intel-grid-2">
        <section className="intel-card">
          <div className="intel-card-header">
            <span className="intel-card-tag">COMMERCIALIZATION PATHWAYS</span>
            <Tag tone="neutral">Routes</Tag>
          </div>
          <h3>Pathways to Market</h3>
          <p className="intel-card-desc">
            Pragmatic routes from prototype to deployment (B2B, licensing, APIs).
          </p>

          {pathways.length ? (
            <div className="intel-item-stack">
              {pathways.map((pw, idx) => (
                <div key={`pw-${idx}`} className="intel-pathway-card">
                  <h4>{pw.pathway}</h4>
                  {pw.description && <p className="pw-desc">{pw.description}</p>}
                  {pw.suitability && (
                    <div className="pw-suitability">
                      <strong>Suitability:</strong> {pw.suitability}
                    </div>
                  )}
                  {pw.milestones?.length > 0 && (
                    <div className="pw-milestones">
                      <strong>Key Milestones:</strong>
                      <ol>
                        {pw.milestones.map((ms, mIdx) => (
                          <li key={`ms-${mIdx}`}>{ms}</li>
                        ))}
                      </ol>
                    </div>
                  )}
                </div>
              ))}
            </div>
          ) : (
            <p className="intel-empty-note">No commercial pathways mapped.</p>
          )}
        </section>

        <section className="intel-card">
          <div className="intel-card-header">
            <span className="intel-card-tag">BUSINESS MODELS</span>
            <Tag tone="neutral">Monetization</Tag>
          </div>
          <h3>Viable Business Models</h3>
          <p className="intel-card-desc">
            Revenue models that logically align with the technical deliverable.
          </p>

          {businessModels.length ? (
            <div className="intel-item-stack">
              {businessModels.map((bm, idx) => (
                <div key={`bm-${idx}`} className="intel-model-card">
                  <div className="model-head">
                    <h4>{bm.model}</h4>
                    <Tag
                      tone={
                        bm.feasibility === "High"
                          ? "supported"
                          : bm.feasibility === "Low"
                          ? "warn"
                          : "neutral"
                      }
                    >
                      {bm.feasibility} Feasibility
                    </Tag>
                  </div>
                  {bm.rationale && <p className="model-rationale">{bm.rationale}</p>}
                </div>
              ))}
            </div>
          ) : (
            <p className="intel-empty-note">No business models identified.</p>
          )}
        </section>
      </div>

      {/* E. Commercialization Barriers */}
      <section className="intel-card">
        <div className="intel-card-header">
          <div>
            <span className="intel-card-tag">RISK MANAGEMENT</span>
            <h3>Commercialization Barriers & Mitigations</h3>
          </div>
          <div className="intel-filter-buttons">
            <button
              className={activeFilter === "all" ? "active" : ""}
              onClick={() => setActiveFilter("all")}
            >
              All ({barriers.length})
            </button>
            <button
              className={activeFilter === "high" ? "active" : ""}
              onClick={() => setActiveFilter("high")}
            >
              High Severity
            </button>
            <button
              className={activeFilter === "medium" ? "active" : ""}
              onClick={() => setActiveFilter("medium")}
            >
              Medium
            </button>
          </div>
        </div>
        <p className="intel-card-desc">
          Technical bottlenecks, regulatory friction, data constraints, and adoption hurdles.
        </p>

        {filteredBarriers.length ? (
          <div className="intel-barrier-list">
            {filteredBarriers.map((b, idx) => (
              <div
                key={`b-${idx}`}
                className={`intel-barrier-item severity-${(b.severity || "medium").toLowerCase()}`}
              >
                <div className="barrier-header">
                  <div className="barrier-meta">
                    <span className="barrier-cat">{b.category || "General"}</span>
                    <Tag
                      tone={
                        b.severity === "High"
                          ? "warn"
                          : b.severity === "Low"
                          ? "supported"
                          : "neutral"
                      }
                    >
                      {b.severity} Risk
                    </Tag>
                  </div>
                  <h4>{b.barrier}</h4>
                </div>
                {b.mitigation && (
                  <div className="barrier-mitigation">
                    <strong>Mitigation Strategy:</strong> {b.mitigation}
                  </div>
                )}
              </div>
            ))}
          </div>
        ) : (
          <p className="intel-empty-note">No barriers found for this filter.</p>
        )}
      </section>

      {/* F. Validation Steps and Next Milestones */}
      <section className="intel-card">
        <div className="intel-card-header">
          <span className="intel-card-tag">TRANSLATIONAL ROADMAP</span>
          <Tag tone="accent">Next Steps</Tag>
        </div>
        <h3>Validation Steps & Roadmap</h3>
        <p className="intel-card-desc">
          Experiments, prototypes, and customer feedback required before commercial deployment.
        </p>

        {validationSteps.length ? (
          <div className="intel-step-list">
            {validationSteps.map((step, idx) => (
              <div key={`step-${idx}`} className="intel-step-card">
                <div className="step-idx-badge">{idx + 1}</div>
                <div className="step-content">
                  <div className="step-head">
                    <span className="step-phase">{step.phase}</span>
                    <h4>{step.action}</h4>
                  </div>
                  {step.validation_goal && (
                    <p className="step-goal">
                      <strong>Validation Goal:</strong> {step.validation_goal}
                    </p>
                  )}
                  {step.missing_evidence && (
                    <p className="step-gap">
                      <strong>Missing Evidence / Gap:</strong> {step.missing_evidence}
                    </p>
                  )}
                </div>
              </div>
            ))}
          </div>
        ) : (
          <p className="intel-empty-note">No validation steps provided.</p>
        )}
      </section>

      {/* Grounded Evidence vs Commercial Hypotheses */}
      <section className="intel-card">
        <div className="intel-card-header">
          <span className="intel-card-tag">EVALUATION RIGOR</span>
          <Tag tone="neutral">Auditing Grounding</Tag>
        </div>
        <h3>Evidence Grounding & Commercial Assumptions</h3>
        <p className="intel-card-desc">
          Audit of factual claims supported directly by the paper vs. AI-generated commercial hypotheses.
        </p>

        {evidenceAndAssumptions.length ? (
          <div className="intel-audit-table-wrap">
            <table className="intel-audit-table">
              <thead>
                <tr>
                  <th>Aspect</th>
                  <th>Classification</th>
                  <th>Detail & Grounding</th>
                  <th>Confidence</th>
                </tr>
              </thead>
              <tbody>
                {evidenceAndAssumptions.map((ea, idx) => (
                  <tr key={`ea-${idx}`}>
                    <td className="ea-aspect">
                      <strong>{ea.aspect}</strong>
                    </td>
                    <td>
                      <Tag
                        tone={
                          ea.type === "paper_evidence"
                            ? "supported"
                            : "accent"
                        }
                      >
                        {ea.type === "paper_evidence"
                          ? "Paper Evidence"
                          : "Commercial Hypothesis"}
                      </Tag>
                    </td>
                    <td className="ea-detail">{ea.detail}</td>
                    <td>
                      <span className={`confidence-tag conf-${ea.confidence}`}>
                        {ea.confidence}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="intel-empty-note">No evidence classification available.</p>
        )}
      </section>

      {/* Warnings & Method Notes */}
      {warnings.length > 0 && (
        <details className="method-notes">
          <summary>Business intelligence method notes ({warnings.length})</summary>
          <ul>
            {warnings.map((w, index) => (
              <li key={`bi-warn-${index}`}>{w}</li>
            ))}
          </ul>
        </details>
      )}
    </div>
  );
}
