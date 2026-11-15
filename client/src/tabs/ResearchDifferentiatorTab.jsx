import { useEffect, useState } from "react";
import { differentiatePaper } from "../api.js";
import { EmptyState, Icon, Tag } from "../components/ui.jsx";
import TabHelperBanner from "../components/TabHelperBanner.jsx";

export default function ResearchDifferentiatorTab({ analysis, isDemo }) {
  const jobId = analysis?.job_id;
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [expandedAbstracts, setExpandedAbstracts] = useState({});
  const [showProfile, setShowProfile] = useState(false);

  const isDemoAnalysis = Boolean(
    isDemo || !jobId || String(jobId).startsWith("demo")
  );

  const fetchDifferentiation = async () => {
    if (isDemoAnalysis || !jobId) return;
    setLoading(true);
    setError(null);
    try {
      const response = await differentiatePaper(jobId);
      setData(response);
    } catch (err) {
      setError(err?.message || "Failed to load research differentiation.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDifferentiation();
  }, [jobId, isDemoAnalysis]);

  const toggleAbstract = (paperId) => {
    setExpandedAbstracts((prev) => ({
      ...prev,
      [paperId]: !prev[paperId],
    }));
  };

  if (isDemoAnalysis) {
    return (
      <div className="tab-stack research-differentiator">
        <section className="intel-hero">
          <div className="intel-hero-copy">
            <span className="gap-eyebrow">RESEARCH DIFFERENTIATOR / LITERATURE DISCOVERY</span>
            <h2>How does this paper differ from prior art?</h2>
            <p>
              Compare your paper against retrieved OpenAlex literature to identify established foundations,
              potential novel contributions, and methodology differences.
            </p>
          </div>
        </section>

        <section className="intel-notice info">
          <div className="intel-notice-header">
            <Icon name="summary" size={18} />
            <strong>Real uploaded paper required</strong>
          </div>
          <p>
            The Research Differentiator requires an uploaded research paper. Demo mode uses static mock data
            that does not support dynamic literature search via OpenAlex or AI comparative synthesis.
            Upload a research PDF or text document from the start screen to explore this feature with live papers.
          </p>
        </section>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="tab-stack research-differentiator">
        <section className="intel-hero">
          <div className="intel-hero-copy">
            <span className="gap-eyebrow">RESEARCH DIFFERENTIATOR / LITERATURE DISCOVERY</span>
            <h2>How does this paper differ from prior art?</h2>
            <p>Comparing against academic literature retrieved via OpenAlex...</p>
          </div>
        </section>

        <div className="intel-loading-card">
          <div className="intel-spinner" aria-hidden="true" />
          <div className="intel-loading-text">
            <h3>Searching literature & synthesizing differentiation</h3>
            <p>
              Extracting the research profile, querying OpenAlex for related works, and analyzing novelty and methodology differences.
            </p>
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="tab-stack research-differentiator">
        <section className="intel-hero">
          <div className="intel-hero-copy">
            <span className="gap-eyebrow">RESEARCH DIFFERENTIATOR / LITERATURE DISCOVERY</span>
            <h2>How does this paper differ from prior art?</h2>
          </div>
        </section>

        <div className="intel-error-card">
          <div className="intel-error-header">
            <Icon name="close" size={18} />
            <h3>Unable to complete differentiation</h3>
          </div>
          <p>{error}</p>
          <button
            type="button"
            className="button"
            onClick={fetchDifferentiation}
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
      <div className="tab-stack research-differentiator">
        <EmptyState title="No differentiation data available">
          Click below to initiate research differentiation against academic literature.
        </EmptyState>
        <button
          type="button"
          className="button"
          onClick={fetchDifferentiation}
          style={{ margin: "16px auto 0", display: "block" }}
        >
          Run Research Differentiator
        </button>
      </div>
    );
  }

  const diff = data.differentiation || data;
  const comparison = data.comparison || diff.comparison || {};
  const relatedPapers = data.related_papers || diff.related_papers || [];
  const searchQuery = data.search_query || diff.search_query || "";
  const profile = data.research_profile?.profile || data.profile || {};
  const warnings = [
    ...(data.warnings || []),
    ...(diff.warnings || []),
  ].filter((w, i, arr) => arr.indexOf(w) === i);

  return (
    <div className="tab-stack research-differentiator">
      <section className="intel-hero">
        <div className="intel-hero-copy">
          <span className="gap-eyebrow">RESEARCH DIFFERENTIATOR / LITERATURE DISCOVERY</span>
          <h2>How does this paper differ from prior art?</h2>
          <p>
            Comparative analysis grounded on retrieved OpenAlex literature and extracted paper profiles.
          </p>
        </div>
        <div className="intel-stat-badge">
          <strong>{relatedPapers.length}</strong>
          <span>papers compared</span>
        </div>
      </section>

      <TabHelperBanner
        emoji="🧭"
        title="Quick Guide: How to read this literature comparison"
        tips={[
          "Search Query: Shows the focused multi-attribute search used to discover relevant papers on OpenAlex.",
          "Established Elements: Identifies techniques or foundational components that were already known in prior art.",
          "Potentially Novel Elements: Highlights what the authors newly propose beyond retrieved baseline literature.",
          "Related Papers: Browse discovered academic works, expand abstracts, and click DOI links to view original publications.",
        ]}
      />

      {/* Scientific Literature-Dependent Disclaimer */}
      <section className="intel-disclaimer">
        <div className="intel-disclaimer-title">
          <Icon name="summary" size={16} />
          <strong>Scientific Interpretation Notice</strong>
        </div>
        <p>
          This novelty and differential assessment is based strictly on retrieved OpenAlex literature and
          their available abstracts. It does not constitute proof that a paper is globally or universally novel.
          Absence of a technique in the retrieved results does not guarantee global absence in all scientific literature.
        </p>
      </section>

      {/* Search Query & Coverage */}
      {searchQuery && (
        <section className="intel-card intel-query-card">
          <div className="intel-card-header">
            <span className="intel-card-tag">LITERATURE SEARCH QUERY</span>
            <span className="intel-query-meta">{relatedPapers.length} works retrieved</span>
          </div>
          <p className="intel-query-text">"{searchQuery}"</p>
        </section>
      )}

      {/* Novelty Assessment Highlight */}
      <section className="intel-card intel-novelty-card">
        <div className="intel-card-header">
          <span className="intel-card-tag">SYNTHESIS</span>
          <Tag tone="accent">Literature Comparison</Tag>
        </div>
        {comparison.overall_assessment && (
          <div className="intel-section-chunk">
            <h3>Overall Assessment</h3>
            <p className="intel-lead-text">{comparison.overall_assessment}</p>
          </div>
        )}
        {comparison.novelty_assessment && (
          <div className="intel-section-chunk">
            <h3>Novelty Assessment</h3>
            <p className="intel-body-text">{comparison.novelty_assessment}</p>
          </div>
        )}
      </section>

      {/* Established vs Potentially Novel Elements */}
      <div className="intel-grid-2">
        <section className="intel-card">
          <div className="intel-card-header">
            <span className="intel-card-tag">ESTABLISHED FOUNDATIONS</span>
            <Tag tone="neutral">Prior Art</Tag>
          </div>
          <h3>Established Elements</h3>
          <p className="intel-card-desc">
            Concepts, methods, or components already established in the retrieved academic literature.
          </p>
          {comparison.established_elements?.length ? (
            <ul className="intel-list established">
              {comparison.established_elements.map((item, idx) => (
                <li key={`est-${idx}`}>
                  <span className="intel-list-bullet">✓</span>
                  <span>{item}</span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="intel-empty-note">No established elements explicitly flagged.</p>
          )}
        </section>

        <section className="intel-card highlight-card">
          <div className="intel-card-header">
            <span className="intel-card-tag">DIFFERENTIATING ELEMENTS</span>
            <Tag tone="supported">Potentially Novel</Tag>
          </div>
          <h3>Potentially Novel Contributions</h3>
          <p className="intel-card-desc">
            Elements proposed in this paper that distinguish it from the retrieved comparative papers.
          </p>
          {comparison.potentially_novel_elements?.length ? (
            <ul className="intel-list novel">
              {comparison.potentially_novel_elements.map((item, idx) => (
                <li key={`nov-${idx}`}>
                  <span className="intel-list-bullet">★</span>
                  <span>{item}</span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="intel-empty-note">No novel elements distinguished from search results.</p>
          )}
        </section>
      </div>

      {/* Methodology, Dataset, and Metric Comparison */}
      <div className="intel-grid-3">
        <section className="intel-card">
          <div className="intel-card-header">
            <span className="intel-card-tag">METHODOLOGY</span>
          </div>
          <h3>Methodology Comparison</h3>
          {comparison.methodology_comparison?.length ? (
            <ul className="intel-list">
              {comparison.methodology_comparison.map((item, idx) => (
                <li key={`meth-${idx}`}>{item}</li>
              ))}
            </ul>
          ) : (
            <p className="intel-empty-note">No methodology comparisons available.</p>
          )}
        </section>

        <section className="intel-card">
          <div className="intel-card-header">
            <span className="intel-card-tag">BENCHMARKS & DATA</span>
          </div>
          <h3>Dataset Comparison</h3>
          {comparison.dataset_comparison?.length ? (
            <ul className="intel-list">
              {comparison.dataset_comparison.map((item, idx) => (
                <li key={`ds-${idx}`}>{item}</li>
              ))}
            </ul>
          ) : (
            <p className="intel-empty-note">No dataset comparisons available.</p>
          )}
        </section>

        <section className="intel-card">
          <div className="intel-card-header">
            <span className="intel-card-tag">METRICS & RESULTS</span>
          </div>
          <h3>Metric & Result Comparison</h3>
          {comparison.metric_and_result_comparison?.length ? (
            <ul className="intel-list">
              {comparison.metric_and_result_comparison.map((item, idx) => (
                <li key={`met-${idx}`}>{item}</li>
              ))}
            </ul>
          ) : (
            <p className="intel-empty-note">No metric comparisons available.</p>
          )}
        </section>
      </div>

      {/* Research Gaps & Uncertainties */}
      <div className="intel-grid-2">
        <section className="intel-card">
          <div className="intel-card-header">
            <span className="intel-card-tag">LITERATURE GAPS</span>
            <Tag tone="warn">Unaddressed</Tag>
          </div>
          <h3>Remaining Research Gaps</h3>
          <p className="intel-card-desc">
            Questions, problem spaces, or limitations not fully solved by either this paper or the retrieved works.
          </p>
          {comparison.research_gaps?.length ? (
            <ul className="intel-list">
              {comparison.research_gaps.map((item, idx) => (
                <li key={`gap-${idx}`}>{item}</li>
              ))}
            </ul>
          ) : (
            <p className="intel-empty-note">No specific research gaps reported.</p>
          )}
        </section>

        <section className="intel-card">
          <div className="intel-card-header">
            <span className="intel-card-tag">EVIDENCE & BOUNDS</span>
            <Tag tone="neutral">Uncertainties</Tag>
          </div>
          <h3>Evidence & Uncertainties</h3>
          <p className="intel-card-desc">
            Caveats, missing abstracts, unverified baselines, or non-comparable experimental setups.
          </p>
          {comparison.evidence_and_uncertainties?.length ? (
            <ul className="intel-list">
              {comparison.evidence_and_uncertainties.map((item, idx) => (
                <li key={`unc-${idx}`}>{item}</li>
              ))}
            </ul>
          ) : (
            <p className="intel-empty-note">No uncertainties reported.</p>
          )}
        </section>
      </div>

      {/* Retrieved Related Papers */}
      <section className="intel-card papers-section">
        <div className="intel-card-header">
          <span className="intel-card-tag">DISCOVERED LITERATURE</span>
          <Tag tone="neutral">OpenAlex Academic Works</Tag>
        </div>
        <h3>Related Academic Papers ({relatedPapers.length})</h3>
        <p className="intel-card-desc">
          Academic papers discovered based on the extracted problem, methodology, and datasets.
        </p>

        {relatedPapers.length ? (
          <div className="intel-paper-list">
            {relatedPapers.map((paper, idx) => {
              const paperKey = paper.id || `paper-${idx}`;
              const isExpanded = Boolean(expandedAbstracts[paperKey]);
              const doiUrl = paper.doi
                ? paper.doi.startsWith("http")
                  ? paper.doi
                  : `https://doi.org/${paper.doi.replace(/^doi:/i, "")}`
                : null;

              return (
                <article key={paperKey} className="intel-paper-item">
                  <div className="intel-paper-top">
                    <span className="intel-paper-idx">{String(idx + 1).padStart(2, "0")}</span>
                    <div className="intel-paper-main">
                      <h4 className="intel-paper-title">
                        {doiUrl ? (
                          <a href={doiUrl} target="_blank" rel="noopener noreferrer" title="Open paper in new tab">
                            {paper.title} ↗
                          </a>
                        ) : (
                          paper.title
                        )}
                      </h4>

                      <div className="intel-paper-meta">
                        {paper.year && <span className="meta-badge">{paper.year}</span>}
                        {paper.venue && <span className="meta-venue">{paper.venue}</span>}
                        {paper.type && <span className="meta-type">{paper.type.replace(/_/g, " ")}</span>}
                        {paper.citations !== undefined && (
                          <span className="meta-citations">{paper.citations} citations</span>
                        )}
                      </div>

                      {paper.authors?.length > 0 && (
                        <p className="intel-paper-authors">
                          Authors: {paper.authors.join(", ")}
                        </p>
                      )}
                    </div>
                  </div>

                  {paper.abstract ? (
                    <div className="intel-abstract-box">
                      <button
                        type="button"
                        className="intel-abstract-toggle"
                        onClick={() => toggleAbstract(paperKey)}
                        aria-expanded={isExpanded}
                      >
                        <span>{isExpanded ? "Hide abstract" : "View abstract"}</span>
                        <span>{isExpanded ? "−" : "+"}</span>
                      </button>
                      {isExpanded && (
                        <p className="intel-abstract-text">{paper.abstract}</p>
                      )}
                    </div>
                  ) : (
                    <span className="intel-no-abstract">Abstract unavailable from OpenAlex index</span>
                  )}

                  {doiUrl && (
                    <div className="intel-paper-footer">
                      <a
                        href={doiUrl}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-button"
                      >
                        DOI: {paper.doi} ↗
                      </a>
                    </div>
                  )}
                </article>
              );
            })}
          </div>
        ) : (
          <EmptyState title="No related papers discovered">
            The literature search did not return matches.
          </EmptyState>
        )}
      </section>

      {/* Extracted Research Profile (Collapsible) */}
      <section className="intel-card profile-section">
        <div className="intel-card-header">
          <span className="intel-card-tag">BASE PAPER GROUNDING</span>
          <button
            type="button"
            className="text-button"
            onClick={() => setShowProfile(!showProfile)}
          >
            {showProfile ? "Hide Research Profile" : "Inspect Extracted Research Profile"}
          </button>
        </div>
        <h3>Extracted Research Profile</h3>
        <p className="intel-card-desc">
          Structured technical representations extracted directly from the uploaded paper.
        </p>

        {showProfile && (
          <div className="intel-profile-grid">
            {profile.research_problem && (
              <div className="profile-item">
                <strong>Research Problem</strong>
                <p>{profile.research_problem}</p>
              </div>
            )}
            {profile.methodology && (
              <div className="profile-item">
                <strong>Methodology</strong>
                <p>{profile.methodology}</p>
              </div>
            )}
            {profile.architecture_or_model && (
              <div className="profile-item">
                <strong>Architecture / Model</strong>
                <p>{profile.architecture_or_model}</p>
              </div>
            )}
            {profile.main_contributions?.length > 0 && (
              <div className="profile-item">
                <strong>Main Contributions</strong>
                <ul>
                  {profile.main_contributions.map((c, i) => (
                    <li key={i}>{c}</li>
                  ))}
                </ul>
              </div>
            )}
            {profile.datasets?.length > 0 && (
              <div className="profile-item">
                <strong>Datasets</strong>
                <p>{profile.datasets.join(", ")}</p>
              </div>
            )}
            {profile.evaluation_metrics?.length > 0 && (
              <div className="profile-item">
                <strong>Evaluation Metrics</strong>
                <p>{profile.evaluation_metrics.join(", ")}</p>
              </div>
            )}
            {profile.limitations?.length > 0 && (
              <div className="profile-item">
                <strong>Author Limitations</strong>
                <ul>
                  {profile.limitations.map((l, i) => (
                    <li key={i}>{l}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}
      </section>

      {/* Warnings & Notes */}
      {warnings.length > 0 && (
        <details className="method-notes">
          <summary>Differentiation & discovery method notes ({warnings.length})</summary>
          <ul>
            {warnings.map((w, index) => (
              <li key={`diff-warn-${index}`}>{w}</li>
            ))}
          </ul>
        </details>
      )}
    </div>
  );
}
