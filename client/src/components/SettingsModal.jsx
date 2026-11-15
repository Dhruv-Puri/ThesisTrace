import { useEffect, useState } from "react";
import { cancelSubscription, getBillingSubscription } from "../api.js";
import { ACCENTS, applyTheme } from "../theme.js";
import { Icon, RingGauge, Tag } from "./ui.jsx";

export default function SettingsModal({
  open,
  onClose,
  theme,
  onThemeChange,
  onOpenPricing,
}) {
  const [activeTab, setActiveTab] = useState("appearance"); // "appearance" | "billing" | "roadmap"
  const [subData, setSubData] = useState(null);
  const [canceling, setCanceling] = useState(false);
  const [previewTheme, setPreviewTheme] = useState(theme);

  useEffect(() => {
    setPreviewTheme(theme);
  }, [theme]);

  useEffect(() => {
    if (!open) return;
    getBillingSubscription()
      .then(setSubData)
      .catch(() => setSubData(null));
  }, [open]);

  if (!open) return null;

  const handleUpdateTheme = (updates) => {
    const next = { ...previewTheme, ...updates };
    setPreviewTheme(next);
    onThemeChange(next);
    applyTheme(next);
  };

  const handleCancelSub = async () => {
    if (!confirm("Are you sure you want to cancel your subscription? You will retain access until the end of your billing cycle.")) {
      return;
    }
    setCanceling(true);
    try {
      const updated = await cancelSubscription();
      setSubData(updated);
      alert("Subscription has been set to cancel at the end of the billing cycle.");
    } catch (err) {
      alert(err.message || "Could not cancel subscription.");
    } finally {
      setCanceling(false);
    }
  };

  const sub = subData?.subscription || { plan_id: "free", plan_name: "Free", status: "active" };
  const usage = subData?.usage || { analyses_used: 1, analyses_max: 3, ai_queries_used: 2, ai_queries_max: 10 };
  const providerStatus = subData?.provider_status || { live_payments_active: false };

  const analysesRatio = usage.analyses_max === -1 ? 0 : Math.min(1, usage.analyses_used / (usage.analyses_max || 1));
  const queriesRatio = usage.ai_queries_max === -1 ? 0 : Math.min(1, usage.ai_queries_used / (usage.ai_queries_max || 1));

  return (
    <div className="bubbly-modal-backdrop" onClick={onClose} role="dialog" aria-modal="true">
      <div className="bubbly-modal settings-modal-shell" onClick={(e) => e.stopPropagation()}>
        {/* Header */}
        <div className="bubbly-modal-header">
          <div className="bubbly-modal-title">
            <span className="bubbly-sparkle-pill">⚙️ Application Settings</span>
            <h2>Settings & Personalization</h2>
            <p>Customize your workspace appearance, manage subscriptions, and monitor usage.</p>
          </div>
          <button
            type="button"
            className="icon-button bubbly-close"
            onClick={onClose}
            aria-label="Close settings"
          >
            <Icon name="close" size={18} />
          </button>
        </div>

        {/* Settings Navigation */}
        <div className="settings-nav-bar" role="tablist" aria-label="Settings sections">
          <button
            type="button"
            className={`settings-nav-btn ${activeTab === "appearance" ? "is-active" : ""}`}
            onClick={() => setActiveTab("appearance")}
            role="tab"
            aria-selected={activeTab === "appearance"}
          >
            <span>🎨</span>
            <span>Appearance & Themes</span>
          </button>
          <button
            type="button"
            className={`settings-nav-btn ${activeTab === "billing" ? "is-active" : ""}`}
            onClick={() => setActiveTab("billing")}
            role="tab"
            aria-selected={activeTab === "billing"}
          >
            <span>💳</span>
            <span>Subscription & Quotas</span>
          </button>
          <button
            type="button"
            className={`settings-nav-btn ${activeTab === "roadmap" ? "is-active" : ""}`}
            onClick={() => setActiveTab("roadmap")}
            role="tab"
            aria-selected={activeTab === "roadmap"}
          >
            <span>🚀</span>
            <span>Enterprise Roadmap</span>
          </button>
        </div>

        {/* Tab 1: Appearance */}
        {activeTab === "appearance" && (
          <div className="settings-body-scroll">
            <div className="settings-section">
              <div className="section-head">
                <h3>A. Color Mode</h3>
                <p>Choose between daytime paper clarity or night-mode high-contrast reading.</p>
              </div>
              <div className="settings-choice-grid">
                <button
                  type="button"
                  className={`theme-card-choice ${previewTheme.mode === "light" ? "is-selected" : ""}`}
                  onClick={() => handleUpdateTheme({ mode: "light" })}
                  aria-pressed={previewTheme.mode === "light"}
                >
                  <div className="theme-mini-swatch light-swatch">
                    <span className="swatch-head" />
                    <span className="swatch-body" />
                  </div>
                  <strong>☀️ Light Mode</strong>
                  <small>Classic warm academic paper style</small>
                </button>

                <button
                  type="button"
                  className={`theme-card-choice ${previewTheme.mode === "dark" ? "is-selected" : ""}`}
                  onClick={() => handleUpdateTheme({ mode: "dark" })}
                  aria-pressed={previewTheme.mode === "dark"}
                >
                  <div className="theme-mini-swatch dark-swatch">
                    <span className="swatch-head" />
                    <span className="swatch-body" />
                  </div>
                  <strong>🌙 Dark Mode</strong>
                  <small>Deep slate contrast for night research</small>
                </button>
              </div>
            </div>

            <div className="settings-section">
              <div className="section-head">
                <h3>B. Interface Style</h3>
                <p>Select your preferred aesthetic mood. Both styles support Light and Dark modes.</p>
              </div>
              <div className="settings-choice-grid">
                <button
                  type="button"
                  className={`theme-card-choice ${previewTheme.style === "professional" ? "is-selected" : ""}`}
                  onClick={() => handleUpdateTheme({ style: "professional" })}
                  aria-pressed={previewTheme.style === "professional"}
                >
                  <div className="style-icon">🏛️</div>
                  <strong>Professional</strong>
                  <small>Minimal, elegant, crisp corners & restrained academic feel</small>
                </button>

                <button
                  type="button"
                  className={`theme-card-choice ${previewTheme.style === "bubbly" ? "is-selected" : ""}`}
                  onClick={() => handleUpdateTheme({ style: "bubbly" })}
                  aria-pressed={previewTheme.style === "bubbly"}
                >
                  <div className="style-icon">🎈</div>
                  <strong>Bubbly</strong>
                  <small>Playful, soft rounded pills, tactile hover lifts & joyful tags</small>
                </button>
              </div>
            </div>

            <div className="settings-section">
              <div className="section-head">
                <h3>C. Coordinated Accent Palette</h3>
                <p>Sets primary buttons, active tab indicators, gauges, and interactive highlights.</p>
              </div>
              <div className="accent-swatches-grid">
                {ACCENTS.map((accent) => (
                  <button
                    key={accent.id}
                    type="button"
                    className={`accent-choice-pill ${previewTheme.accent === accent.id ? "is-selected" : ""}`}
                    onClick={() => handleUpdateTheme({ accent: accent.id })}
                    aria-label={`${accent.label}${previewTheme.accent === accent.id ? ", selected" : ""}`}
                    aria-pressed={previewTheme.accent === accent.id}
                  >
                    <span className="accent-dot" style={{ backgroundColor: accent.color }} />
                    <span className="accent-name">{accent.label}</span>
                    {previewTheme.accent === accent.id && <span className="accent-check">✓</span>}
                  </button>
                ))}
              </div>
            </div>

            {/* Live Interactive Preview Box */}
            <div className="settings-section">
              <div className="section-head">
                <h3>Live Theme Preview</h3>
                <p>Instant preview showing how controls, tabs, and cards render with your choices:</p>
              </div>
              <div
                className="live-preview-box"
                data-theme={previewTheme.mode}
                data-style={previewTheme.style}
                data-accent={previewTheme.accent}
              >
                <div className="preview-mini-header">
                  <div>
                    <span className="preview-eyebrow">RESEARCH ANALYSIS</span>
                    <h4>Adaptive Sparsity for Neural Translation</h4>
                  </div>
                  <Tag tone="accent">TRL 4 / Lab Validation</Tag>
                </div>
                <div className="preview-mini-tabs">
                  <span className="mini-tab is-active">Summary</span>
                  <span className="mini-tab">Claims</span>
                  <span className="mini-tab">Differentiator</span>
                </div>
                <div className="preview-mini-content">
                  <p>Inference latency cut by 42% on WMT14 benchmarks.</p>
                  <div className="preview-mini-actions">
                    <button type="button" className="button">Primary Action</button>
                    <button type="button" className="button quiet">Secondary</button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Tab 2: Subscription & Billing */}
        {activeTab === "billing" && (
          <div className="settings-body-scroll">
            <div className="settings-section">
              <div className="sub-overview-card">
                <div className="sub-card-header">
                  <div>
                    <span className="sub-tier-label">CURRENT PLAN</span>
                    <h3 className="sub-plan-title">{sub.plan_name} Tier</h3>
                    <p className="sub-status-line">
                      Status: <strong className="status-highlight">{sub.status.toUpperCase()}</strong>
                      {sub.cancel_at_period_end && <span className="cancel-warning"> (Cancels at period end)</span>}
                    </p>
                  </div>
                  <Tag tone={sub.plan_id === "free" ? "neutral" : "supported"}>
                    {sub.plan_id === "free" ? "Free Tier" : "Pro Member"}
                  </Tag>
                </div>

                <div className="sub-actions-row">
                  <button
                    type="button"
                    className="button"
                    onClick={() => {
                      onClose();
                      onOpenPricing();
                    }}
                  >
                    View All Plans & Upgrade 💎
                  </button>
                  {sub.plan_id !== "free" && !sub.cancel_at_period_end && (
                    <button
                      type="button"
                      className="button quiet danger-quiet"
                      disabled={canceling}
                      onClick={handleCancelSub}
                    >
                      {canceling ? "Canceling..." : "Cancel Subscription"}
                    </button>
                  )}
                </div>
              </div>
            </div>

            {/* Quota & Usage Section */}
            <div className="settings-section">
              <div className="section-head">
                <h3>Monthly Account Quotas</h3>
                <p>Usage resets at the beginning of each billing cycle.</p>
              </div>

              <div className="usage-bars-grid">
                <div className="usage-metric-card">
                  <div className="usage-metric-head">
                    <strong>Paper Analyses</strong>
                    <span>
                      {usage.analyses_used} / {usage.analyses_max === -1 ? "Unlimited" : usage.analyses_max}
                    </span>
                  </div>
                  <div className="meter-track">
                    <span
                      className="meter-fill meter-accent"
                      style={{ width: `${usage.analyses_max === -1 ? 15 : analysesRatio * 100}%` }}
                    />
                  </div>
                  <small className="usage-metric-note">
                    {usage.analyses_max === -1
                      ? "Unlimited analyses on your plan."
                      : `${Math.max(0, usage.analyses_max - usage.analyses_used)} analyses remaining this month.`}
                  </small>
                </div>

                <div className="usage-metric-card">
                  <div className="usage-metric-head">
                    <strong>AI Chatbot Queries</strong>
                    <span>
                      {usage.ai_queries_used} / {usage.ai_queries_max === -1 ? "Unlimited" : usage.ai_queries_max}
                    </span>
                  </div>
                  <div className="meter-track">
                    <span
                      className="meter-fill meter-supported"
                      style={{ width: `${usage.ai_queries_max === -1 ? 10 : queriesRatio * 100}%` }}
                    />
                  </div>
                  <small className="usage-metric-note">
                    {usage.ai_queries_max === -1
                      ? "Unlimited grounded AI questions."
                      : `${Math.max(0, usage.ai_queries_max - usage.ai_queries_used)} queries remaining this month.`}
                  </small>
                </div>
              </div>
            </div>

            {/* Payment Gateway Configuration Notice */}
            <div className="settings-section">
              <div className="gateway-status-box">
                <h4>Payment Gateway Status</h4>
                <div className="gateway-row">
                  <span>Stripe Gateway (International):</span>
                  <Tag tone={providerStatus.stripe_configured ? "supported" : "neutral"}>
                    {providerStatus.stripe_configured ? "Configured" : "Not Configured"}
                  </Tag>
                </div>
                <div className="gateway-row">
                  <span>Razorpay Gateway (India / UPI):</span>
                  <Tag tone={providerStatus.razorpay_configured ? "supported" : "neutral"}>
                    {providerStatus.razorpay_configured ? "Configured" : "Not Configured"}
                  </Tag>
                </div>
                <p className="gateway-footer-note">
                  ThesisTrace never stores raw payment credentials. Live payments run through direct HTTPS checkout
                  sessions when configured in the deployment's <code>.env</code>.
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Tab 3: Institutional Roadmap */}
        {activeTab === "roadmap" && (
          <div className="settings-body-scroll">
            <div className="settings-section">
              <div className="section-head">
                <h3>Institutional Architecture & Future Capabilities</h3>
                <p>Commercial research capabilities prepared in ThesisTrace:</p>
              </div>

              <div className="roadmap-grid">
                <div className="roadmap-card">
                  <span className="roadmap-icon">👥</span>
                  <h4>Shared Research Workspaces</h4>
                  <p>
                    Pool papers across PhD research groups, share annotated evidence chains, and maintain a shared
                    literature bibliography.
                  </p>
                  <Tag tone="accent">Lab Plan</Tag>
                </div>

                <div className="roadmap-card">
                  <span className="roadmap-icon">🏛️</span>
                  <h4>Campus SAML / SSO Integration</h4>
                  <p>
                    Authenticate faculty and students through university identity providers (Shibboleth, Google Workspace, Okta).
                  </p>
                  <Tag tone="neutral">Institution</Tag>
                </div>

                <div className="roadmap-card">
                  <span className="roadmap-icon">⚡</span>
                  <h4>Batch Ingestion API</h4>
                  <p>
                    Programmatically submit hundreds of conference or thesis submissions via REST API with webhook callbacks.
                  </p>
                  <Tag tone="neutral">Enterprise</Tag>
                </div>

                <div className="roadmap-card">
                  <span className="roadmap-icon">🔒</span>
                  <h4>Private Air-Gapped Deployments</h4>
                  <p>
                    Run ThesisTrace on isolated university hardware or AWS GovCloud with offline local NLP embeddings.
                  </p>
                  <Tag tone="neutral">Custom</Tag>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Footer */}
        <div className="bubbly-modal-footer">
          <span className="bubbly-footer-note">
            ThesisTrace v0.2.0 SaaS Edition · Preference changes take effect immediately.
          </span>
          <button type="button" className="button" onClick={onClose}>
            Done
          </button>
        </div>
      </div>
    </div>
  );
}
