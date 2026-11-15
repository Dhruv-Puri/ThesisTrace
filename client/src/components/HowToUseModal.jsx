import { useState } from "react";
import { Icon, Tag } from "./ui.jsx";

const GUIDE_ITEMS = [
  {
    id: "summary",
    title: "Summary Tab",
    badge: "The 60-Second Brief",
    icon: "summary",
    emoji: "📑",
    whatIsIt: "Gives you a rapid, executive breakdown of the paper's core premise, methods, and structure.",
    howToUse: [
      "Review the 3-bullet executive summary for the core thesis.",
      "Inspect the Content Coverage Radar to see technical density, vocabulary mix, and structural balance.",
      "Browse extracted key concepts categorized by Datasets, Models, Metrics, and Technical Methods.",
    ],
    proTip: "If you're reviewing many papers, check the top three glance rings first: claims supported, TRL level, and reproducibility score.",
  },
  {
    id: "claims",
    title: "Claims Tab",
    badge: "The Scientific Fact-Checker",
    icon: "claims",
    emoji: "⚖️",
    whatIsIt: "Audits whether the paper's boldest experimental and theoretical claims are backed by its own text and citations.",
    howToUse: [
      "Filter claims by 'Supported', 'Partially Supported', or 'Insufficient Evidence'.",
      "Click any claim card to expand its detailed evidence chain.",
      "Look at the exact page numbers and verbatim passage quotes retrieved from the paper.",
    ],
    proTip: "Pay special attention to 'Insufficient Evidence' claims—these often indicate unproven future promises or unbenchmarked assertions.",
  },
  {
    id: "readiness",
    title: "Readiness Tab",
    badge: "The Reality Check",
    icon: "readiness",
    emoji: "🚀",
    whatIsIt: "Measures real-world engineering maturity using NASA's Technology Readiness Level (TRL 1–9) and a 12-point scientific reproducibility score.",
    howToUse: [
      "Check the TRL Gauge: Levels 1–3 = lab principles & theory; Levels 4–6 = prototype & validation; Levels 7–9 = deployment & operations.",
      "Audit the 12-point Reproducibility Checklist for code availability, dataset links, compute specs, and hyperparameter disclosures.",
      "Review the concrete evidence citations that justified the assigned readiness score.",
    ],
    proTip: "A high claim accuracy with a low TRL (e.g., TRL 2) means the math is sound, but real-world engineering hasn't started yet.",
  },
  {
    id: "gaps",
    title: "Research Gaps Tab",
    badge: "The Blind-Spot Spotter",
    icon: "summary",
    emoji: "🔍",
    whatIsIt: "Surfaces unresolved questions, author-acknowledged limitations, and methodological gaps.",
    howToUse: [
      "Filter by category: Author-reported limitations, Methodological gaps, or Evidence gaps.",
      "Click 'Explore evidence' to inspect the related claim and context passages.",
      "Check the 'Scientific Interpretation' safeguards box at the bottom for critical caveats.",
    ],
    proTip: "Perfect for thesis students looking for their next project topic or engineers looking for potential failure modes.",
  },
  {
    id: "differentiator",
    title: "Research Differentiator",
    badge: "The Prior Art Radar",
    icon: "sparkles",
    emoji: "🧭",
    whatIsIt: "Connects to live academic literature via OpenAlex to compare this paper against existing published works.",
    howToUse: [
      "Read the Novelty Assessment to see how the paper stands out from retrieved literature.",
      "Compare 'Established Elements' (what prior art already did) with 'Potentially Novel Elements' (what this paper actually introduces).",
      "Inspect the Retrieved Papers list and click any DOI link to open the source paper in a new tab.",
      "Expand abstracts to see how similar approaches tackled the same problem.",
    ],
    proTip: "Novelty is evaluated relative to retrieved OpenAlex literature. Use it as a literature comparison guide, not definitive patent proof.",
  },
  {
    id: "business",
    title: "Business Intelligence",
    badge: "The Commercial Translator",
    icon: "lightbulb",
    emoji: "💡",
    whatIsIt: "Translates abstract research into practical product opportunities, customer personas, viable business models, and launch hurdles.",
    howToUse: [
      "Browse Real-World Application Areas to identify target domains and concrete use cases.",
      "Explore Product & Service Opportunities (APIs, developer SDKs, enterprise software, or platforms).",
      "Review Viable Business Models (usage-based, licensing, open-core) and Market Pathways.",
      "Filter Commercialization Barriers by severity (High / Medium) to see what engineering and regulatory hurdles must be cleared.",
      "Follow the Validation Roadmap to know what experiments or customer discovery must happen next.",
    ],
    proTip: "Notice the 'Evidence Grounding' table at the bottom—it separates hard paper facts from AI-generated commercial hypotheses.",
  },
  {
    id: "report",
    title: "Report Tab",
    badge: "The One-Click Briefing",
    icon: "report",
    emoji: "📝",
    whatIsIt: "Generates an executive Markdown briefing summarizing all findings in clean, publishable prose.",
    howToUse: [
      "Click 'Download Markdown' or 'Copy report' to export the memo.",
      "Share it with advisors, funding panels, technology transfer offices, or teammates.",
    ],
    proTip: "The report includes evidence citations and checklist scores, making it a credible, audit-ready document.",
  },
  {
    id: "ask",
    title: "Ask Paper (Chat)",
    badge: "The Grounded Assistant",
    icon: "chat",
    emoji: "💬",
    whatIsIt: "An interactive Q&A assistant powered by Gemini that answers questions strictly from the paper's text and findings.",
    howToUse: [
      "Click the 'Ask' button in the top navigation bar at any time.",
      "Choose one of the quick starter questions or ask anything specific (e.g. 'What datasets did they use?').",
      "Hover over cited sources to verify the exact sentences behind each answer.",
    ],
    proTip: "Ask will refuse to hallucinate; if the authors didn't state something in the text, it will tell you clearly.",
  },
];

export default function HowToUseModal({ open, onClose }) {
  const [selectedId, setSelectedId] = useState("summary");

  if (!open) return null;

  const activeItem = GUIDE_ITEMS.find((item) => item.id === selectedId) || GUIDE_ITEMS[0];

  return (
    <div className="bubbly-modal-backdrop" onClick={onClose} role="dialog" aria-modal="true">
      <div className="bubbly-modal" onClick={(e) => e.stopPropagation()}>
        <div className="bubbly-modal-header">
          <div className="bubbly-modal-title">
            <span className="bubbly-sparkle-pill">✨ Interactive Guide</span>
            <h2>How to Use ThesisTrace</h2>
            <p>Everything you need to know about navigating your research analysis.</p>
          </div>
          <button
            type="button"
            className="icon-button bubbly-close"
            onClick={onClose}
            aria-label="Close guide"
          >
            <Icon name="close" size={18} />
          </button>
        </div>

        <div className="bubbly-guide-container">
          <nav className="bubbly-guide-nav" aria-label="Feature list">
            {GUIDE_ITEMS.map((item) => (
              <button
                key={item.id}
                type="button"
                className={`bubbly-nav-pill ${selectedId === item.id ? "is-active" : ""}`}
                onClick={() => setSelectedId(item.id)}
              >
                <span className="bubbly-nav-emoji">{item.emoji}</span>
                <span className="bubbly-nav-label">{item.title}</span>
              </button>
            ))}
          </nav>

          <article className="bubbly-guide-content">
            <div className="bubbly-content-head">
              <div className="bubbly-item-badge">
                <span className="bubbly-big-emoji">{activeItem.emoji}</span>
                <div>
                  <Tag tone="accent">{activeItem.badge}</Tag>
                  <h3>{activeItem.title}</h3>
                </div>
              </div>
            </div>

            <div className="bubbly-content-section">
              <h4>🎯 What does it do?</h4>
              <p>{activeItem.whatIsIt}</p>
            </div>

            <div className="bubbly-content-section">
              <h4>📋 How to use it:</h4>
              <ul className="bubbly-step-list">
                {activeItem.howToUse.map((step, idx) => (
                  <li key={idx}>
                    <span className="bubbly-num-badge">{idx + 1}</span>
                    <span>{step}</span>
                  </li>
                ))}
              </ul>
            </div>

            <div className="bubbly-pro-tip">
              <span className="bubbly-tip-icon">💡</span>
              <div>
                <strong>Pro-Tip:</strong>
                <p>{activeItem.proTip}</p>
              </div>
            </div>
          </article>
        </div>

        <div className="bubbly-modal-footer">
          <span className="bubbly-footer-note">🎈 Click any feature on the left to learn its superpowers!</span>
          <button type="button" className="button bubbly-button-pop" onClick={onClose}>
            Got it, let's explore! 🚀
          </button>
        </div>
      </div>
    </div>
  );
}
