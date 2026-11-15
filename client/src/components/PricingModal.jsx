import { useEffect, useState } from "react";
import { createCheckoutSession, getBillingPlans, updatePlan } from "../api.js";
import { Icon, Tag } from "./ui.jsx";

export default function PricingModal({ open, onClose, currentPlan = "free", onPlanUpdated }) {
  const [plansData, setPlansData] = useState(null);
  const [interval, setInterval] = useState("year"); // "month" | "year"
  const [loading, setLoading] = useState(false);
  const [checkoutNotice, setCheckoutNotice] = useState(null);
  const [simulating, setSimulating] = useState(false);
  const [openFaq, setOpenFaq] = useState({});

  useEffect(() => {
    if (!open) return;
    getBillingPlans()
      .then(setPlansData)
      .catch(() => setPlansData(null));
  }, [open]);

  if (!open) return null;

  const plans = plansData?.plans || [];
  const faqs = plansData?.faq || [];

  const handlePlanSelect = async (plan) => {
    if (plan.id === currentPlan) return;

    if (plan.id === "institution") {
      alert("For university-wide or institutional deployment, please contact: enterprise@thesistrace.edu");
      return;
    }

    setLoading(true);
    setCheckoutNotice(null);
    try {
      const res = await createCheckoutSession(plan.id, interval, "stripe");
      if (res.status === "ready" && res.checkout_url) {
        window.location.href = res.checkout_url;
      } else {
        // Unconfigured or demo mode
        setCheckoutNotice(res);
      }
    } catch (err) {
      alert(err.message || "Failed to initialize checkout.");
    } finally {
      setLoading(false);
    }
  };

  const handleSimulatePlan = async (planId) => {
    setSimulating(true);
    try {
      await updatePlan(planId, interval);
      if (onPlanUpdated) onPlanUpdated(planId);
      setCheckoutNotice(null);
      onClose();
    } catch (err) {
      alert(err.message || "Could not update plan.");
    } finally {
      setSimulating(false);
    }
  };

  const toggleFaq = (index) => {
    setOpenFaq((prev) => ({ ...prev, [index]: !prev[index] }));
  };

  return (
    <div className="bubbly-modal-backdrop" onClick={onClose} role="dialog" aria-modal="true">
      <div className="bubbly-modal pricing-modal-shell" onClick={(e) => e.stopPropagation()}>
        {/* Header */}
        <div className="bubbly-modal-header">
          <div className="bubbly-modal-title">
            <span className="bubbly-sparkle-pill">💎 Commercial Subscription Plans</span>
            <h2>Flexible Plans for Every Stage of Research</h2>
            <p>From single thesis paper verification to campus-wide research intelligence.</p>
          </div>
          <button
            type="button"
            className="icon-button bubbly-close"
            onClick={onClose}
            aria-label="Close pricing"
          >
            <Icon name="close" size={18} />
          </button>
        </div>

        <div className="pricing-modal-body">
          {/* Interval Toggle */}
          <div className="pricing-toggle-wrap">
            <div className="pricing-interval-segmented">
              <button
                type="button"
                className={interval === "month" ? "is-active" : ""}
                onClick={() => setInterval("month")}
                aria-pressed={interval === "month"}
              >
                Monthly Billing
              </button>
              <button
                type="button"
                className={interval === "year" ? "is-active" : ""}
                onClick={() => setInterval("year")}
                aria-pressed={interval === "year"}
              >
                Annual Billing
                <span className="save-badge">Save ~20%</span>
              </button>
            </div>
            <span className="pricing-guarantee-note">
              🔒 Proposed SaaS pricing · Cancel or switch plans anytime.
            </span>
          </div>

          {/* Checkout Configuration Modal / Overlay if triggered */}
          {checkoutNotice && (
            <div className="checkout-notice-card">
              <div className="notice-head">
                <span className="notice-icon">⚙️</span>
                <div>
                  <h4>Payment Gateway Setup Notice</h4>
                  <p>{checkoutNotice.message}</p>
                </div>
              </div>

              <div className="notice-env-box">
                <strong>To activate live Stripe or Razorpay checkouts, set in .env:</strong>
                <code>
                  STRIPE_SECRET_KEY=sk_live_...<br />
                  STRIPE_WEBHOOK_SECRET=whsec_...<br />
                  # or for India / UPI / NetBanking:<br />
                  RAZORPAY_KEY_ID=rzp_live_...<br />
                  RAZORPAY_KEY_SECRET=...
                </code>
              </div>

              <div className="notice-actions">
                <button
                  type="button"
                  className="button"
                  disabled={simulating}
                  onClick={() => handleSimulatePlan(checkoutNotice.plan_id)}
                >
                  {simulating ? "Activating..." : `Activate ${checkoutNotice.plan_name} (Local Demo Mode)`}
                </button>
                <button
                  type="button"
                  className="button quiet"
                  onClick={() => setCheckoutNotice(null)}
                >
                  Dismiss
                </button>
              </div>
            </div>
          )}

          {/* Plan Cards Grid */}
          <div className="pricing-cards-grid">
            {plans.map((plan) => {
              const isCurrent = plan.id === currentPlan;
              const price = interval === "year" ? plan.price_annual_monthly : plan.price_monthly;
              const periodLabel = plan.is_custom ? "" : interval === "year" ? "/ mo (billed annually)" : "/ month";

              return (
                <div
                  key={plan.id}
                  className={`pricing-plan-card ${plan.highlighted ? "is-recommended" : ""} ${
                    isCurrent ? "is-current" : ""
                  }`}
                >
                  {plan.highlighted && (
                    <div className="plan-recommended-ribbon">⭐ Most Popular</div>
                  )}

                  <div className="plan-card-top">
                    <div className="plan-badge-row">
                      <Tag tone={plan.highlighted ? "accent" : "neutral"}>{plan.badge}</Tag>
                      {isCurrent && <Tag tone="supported">Active Plan</Tag>}
                    </div>
                    <h3 className="plan-name">{plan.name}</h3>
                    <p className="plan-tagline">{plan.tagline}</p>
                  </div>

                  <div className="plan-price-block">
                    {plan.is_custom ? (
                      <div className="price-custom">
                        <strong>Custom</strong>
                        <span>Campus or Lab licensing</span>
                      </div>
                    ) : (
                      <div className="price-numeric">
                        <span className="price-currency">$</span>
                        <strong className="price-value">{price}</strong>
                        <span className="price-period">{periodLabel}</span>
                      </div>
                    )}
                    {interval === "year" && plan.annual_discount_percent > 0 && (
                      <span className="annual-savings-sub">
                        Save {plan.annual_discount_percent}% with annual billing
                      </span>
                    )}
                  </div>

                  <button
                    type="button"
                    className={`button plan-cta-btn ${plan.highlighted ? "highlighted-btn" : "quiet"}`}
                    disabled={isCurrent || loading}
                    onClick={() => handlePlanSelect(plan)}
                  >
                    {isCurrent ? "Current Plan" : plan.cta}
                  </button>

                  <div className="plan-features-list">
                    <span className="features-head">Included capabilities:</span>
                    <ul>
                      {plan.features.map((feat, fIdx) => (
                        <li key={fIdx}>
                          <span className="feat-check">✓</span>
                          <span>{feat}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                </div>
              );
            })}
          </div>

          {/* Feature Comparison Matrix */}
          <section className="pricing-matrix-section">
            <div className="matrix-head">
              <h3>Detailed Feature Matrix</h3>
              <p>Compare allowances and tools across all ThesisTrace subscription tiers.</p>
            </div>

            <div className="matrix-table-wrap">
              <table className="matrix-table">
                <thead>
                  <tr>
                    <th>Capability</th>
                    <th>Free</th>
                    <th>Pro</th>
                    <th>Lab</th>
                    <th>Institution</th>
                  </tr>
                </thead>
                <tbody>
                  <tr>
                    <td><strong>Monthly Paper Analyses</strong></td>
                    <td>3 papers / mo</td>
                    <td>50 papers / mo</td>
                    <td>250 papers / mo</td>
                    <td>Unlimited</td>
                  </tr>
                  <tr>
                    <td><strong>AI Chatbot Queries (Gemini)</strong></td>
                    <td>10 queries / mo</td>
                    <td>150 queries / mo</td>
                    <td>1,000 queries / mo</td>
                    <td>Unlimited</td>
                  </tr>
                  <tr>
                    <td><strong>Max Document Size</strong></td>
                    <td>15 MB</td>
                    <td>30 MB</td>
                    <td>50 MB</td>
                    <td>100 MB</td>
                  </tr>
                  <tr>
                    <td><strong>Research Differentiator (OpenAlex)</strong></td>
                    <td>Basic preview</td>
                    <td>Full access</td>
                    <td>Full access</td>
                    <td>Full access</td>
                  </tr>
                  <tr>
                    <td><strong>Business Intelligence & Translation</strong></td>
                    <td>Preview</td>
                    <td>Full access</td>
                    <td>Full access</td>
                    <td>Full access</td>
                  </tr>
                  <tr>
                    <td><strong>Multi-Paper Research Portfolios</strong></td>
                    <td>1 portfolio</td>
                    <td>10 portfolios</td>
                    <td>50 portfolios</td>
                    <td>Unlimited</td>
                  </tr>
                  <tr>
                    <td><strong>Team Workspaces & Member Seats</strong></td>
                    <td>1 seat</td>
                    <td>1 seat</td>
                    <td>Up to 10 seats</td>
                    <td>Custom site license</td>
                  </tr>
                  <tr>
                    <td><strong>Export Formats</strong></td>
                    <td>Markdown summary</td>
                    <td>Markdown, JSON, Data</td>
                    <td>Full Lab exports</td>
                    <td>Custom APIs & DB</td>
                  </tr>
                  <tr>
                    <td><strong>Deployment Options</strong></td>
                    <td>Local / Web</td>
                    <td>Cloud SaaS</td>
                    <td>Cloud SaaS</td>
                    <td>On-Premise / VPC</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </section>

          {/* FAQ Accordion */}
          <section className="pricing-faq-section">
            <h3>Frequently Asked Questions</h3>
            <div className="faq-list">
              {faqs.map((faq, index) => {
                const isOpen = Boolean(openFaq[index]);
                return (
                  <div key={index} className={`faq-item ${isOpen ? "is-open" : ""}`}>
                    <button
                      type="button"
                      className="faq-question-btn"
                      onClick={() => toggleFaq(index)}
                      aria-expanded={isOpen}
                    >
                      <span>{faq.question}</span>
                      <span className="faq-chevron">{isOpen ? "−" : "+"}</span>
                    </button>
                    {isOpen && <p className="faq-answer">{faq.answer}</p>}
                  </div>
                );
              })}
            </div>
          </section>
        </div>

        <div className="bubbly-modal-footer">
          <span className="bubbly-footer-note">
            💡 Educational lab lead? Contact us for multi-year academic research grant billing.
          </span>
          <button type="button" className="button quiet" onClick={onClose}>
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
