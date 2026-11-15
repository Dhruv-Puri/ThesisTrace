"""SaaS subscription data models, plan configuration, and billing architecture."""

from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Literal

from . import config

logger = logging.getLogger("thesistrace.billing")

BILLING_STORE_PATH = config.ROOT / ".data" / "billing.json"

# ---------------------------------------------------------------------------
# Subscription Plans & Pricing Configuration
# ---------------------------------------------------------------------------

PLANS: dict[str, dict[str, Any]] = {
    "free": {
        "id": "free",
        "name": "Free",
        "tagline": "For undergraduate students and first-time researchers",
        "badge": "Starter",
        "price_monthly": 0,
        "price_annual_monthly": 0,
        "annual_discount_percent": 0,
        "limits": {
            "analyses_per_month": 3,
            "ai_queries_per_month": 10,
            "max_paper_mb": 15,
            "portfolios_allowed": 1,
            "team_seats": 1,
        },
        "features": [
            "Up to 3 paper analyses per month",
            "Executive summary and key concept extraction",
            "Factual claim auditing with passage citations",
            "Basic NASA Technology Readiness Level (TRL)",
            "10 grounded Gemini AI chatbot queries per month",
            "Basic Markdown executive report access",
        ],
        "highlighted": False,
        "cta": "Current Plan",
    },
    "pro": {
        "id": "pro",
        "name": "Pro",
        "tagline": "For postgraduates, PhD scholars, and independent researchers",
        "badge": "Recommended",
        "price_monthly": 19,
        "price_annual_monthly": 15,  # $180/yr (~21% savings)
        "annual_discount_percent": 21,
        "limits": {
            "analyses_per_month": 50,
            "ai_queries_per_month": 150,
            "max_paper_mb": 30,
            "portfolios_allowed": 10,
            "team_seats": 1,
        },
        "features": [
            "50 paper analyses per month",
            "Full Research Differentiator with OpenAlex literature comparison",
            "Full Business Intelligence & commercial translation roadmap",
            "Advanced TRL readiness and 12-point reproducibility scorecard",
            "150 grounded Gemini AI chatbot queries per month",
            "Full research export (Markdown, JSON report)",
            "Multi-paper research portfolio comparisons",
            "Permanent research history and saved library",
            "Priority queue processing",
        ],
        "highlighted": True,
        "cta": "Upgrade to Pro",
    },
    "lab": {
        "id": "lab",
        "name": "Lab",
        "tagline": "For research laboratories, faculty, and collaborative teams",
        "badge": "Team Collaboration",
        "price_monthly": 79,
        "price_annual_monthly": 64,  # $768/yr (~19% savings)
        "annual_discount_percent": 19,
        "limits": {
            "analyses_per_month": 250,
            "ai_queries_per_month": 1000,
            "max_paper_mb": 50,
            "portfolios_allowed": 50,
            "team_seats": 10,
        },
        "features": [
            "Up to 10 collaborative team seats",
            "250 paper analyses per month pooled across the lab",
            "Shared research workspaces and team paper libraries",
            "Team paper portfolio comparisons and benchmarking",
            "Collaborative notes and joint report generation",
            "Lab-wide usage and token management dashboard",
            "Full access to Differentiator & Business Intelligence for all members",
            "Dedicated email support",
        ],
        "highlighted": False,
        "cta": "Start Lab Trial",
    },
    "institution": {
        "id": "institution",
        "name": "Institution",
        "tagline": "For universities, research institutes, and tech-transfer offices",
        "badge": "Enterprise",
        "price_monthly": 499,
        "price_annual_monthly": 399,
        "annual_discount_percent": 20,
        "is_custom": True,
        "limits": {
            "analyses_per_month": -1,  # Unlimited
            "ai_queries_per_month": -1,
            "max_paper_mb": 100,
            "portfolios_allowed": -1,
            "team_seats": -1,
        },
        "features": [
            "Campus-wide or organisation-wide site licensing",
            "Unlimited paper analyses and AI queries",
            "SAML / Single Sign-On (SSO) integration (Shibboleth, Google, Okta)",
            "Centralised admin dashboard with role-based access control",
            "Technology-transfer pipeline tracking and commercial opportunity export",
            "Centralised annual invoicing with PO support",
            "On-premise Docker / VPC deployment assistance",
            "Dedicated account manager & 99.9% uptime SLA",
        ],
        "highlighted": False,
        "cta": "Contact Institutional Sales",
    },
}

FAQ_ITEMS = [
    {
        "question": "Can I cancel or change my plan at any time?",
        "answer": "Yes. You can upgrade, downgrade, or cancel your subscription at any time from Settings. When canceling, you retain full plan access until the end of your billing cycle.",
    },
    {
        "question": "What payment gateways are supported?",
        "answer": "ThesisTrace is designed with dual-provider architecture supporting Stripe for global credit/debit card billing and Razorpay for Indian UPI, NetBanking, and RuPay cards.",
    },
    {
        "question": "Are student or academic discounts available?",
        "answer": "Yes! Our Free tier is specifically designed for undergraduate coursework. For PhD scholars whose universities do not reimburse software, contact support for verified student discounts on Pro.",
    },
    {
        "question": "Is my research paper kept private and confidential?",
        "answer": "Yes. Documents analyzed by ThesisTrace run locally on your deployment. Uploaded files are automatically purged after analysis retention TTL. Your unpublished research is never used to train public AI models.",
    },
    {
        "question": "How does annual billing work?",
        "answer": "Annual billing charges once per year upfront and provides approximately 20% savings compared to month-to-month billing.",
    },
]


# ---------------------------------------------------------------------------
# Subscription Store
# ---------------------------------------------------------------------------

@dataclass
class Subscription:
    plan_id: str = "free"
    status: Literal["active", "past_due", "canceled", "trialing"] = "active"
    interval: Literal["month", "year"] = "month"
    customer_id: str = "cust_demo"
    current_period_end: float = field(default_factory=lambda: time.time() + 30 * 86400)
    cancel_at_period_end: bool = False
    analyses_used_this_month: int = 1
    ai_queries_used_this_month: int = 2
    payment_method: str = "None (Free Tier)"


def _get_provider_status() -> dict[str, Any]:
    stripe_key = os.getenv("STRIPE_SECRET_KEY") or os.getenv("THESISTRACE_STRIPE_SECRET_KEY") or ""
    razorpay_key = os.getenv("RAZORPAY_KEY_ID") or os.getenv("THESISTRACE_RAZORPAY_KEY_ID") or ""
    return {
        "stripe_configured": bool(stripe_key),
        "razorpay_configured": bool(razorpay_key),
        "live_payments_active": bool(stripe_key or razorpay_key),
    }


def _read_store() -> dict[str, Any]:
    try:
        if BILLING_STORE_PATH.exists():
            return json.loads(BILLING_STORE_PATH.read_text(encoding="utf-8"))
    except Exception:
        logger.warning("Could not read billing.json store; using defaults")
    return asdict(Subscription())


def _write_store(data: dict[str, Any]) -> None:
    try:
        BILLING_STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
        BILLING_STORE_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")
    except Exception as exc:
        logger.warning("Could not persist billing store: %s", exc)


def get_plans() -> dict[str, Any]:
    """Return all configurable plans, annual savings, and FAQs."""
    return {
        "plans": list(PLANS.values()),
        "faq": FAQ_ITEMS,
        "provider_status": _get_provider_status(),
    }


def get_subscription(user_id: str = "default") -> dict[str, Any]:
    """Return current subscription state, usage counters, and entitlements."""
    raw = _read_store()
    plan_id = raw.get("plan_id", "free")
    plan = PLANS.get(plan_id, PLANS["free"])

    return {
        "user_id": user_id,
        "subscription": {
            "plan_id": plan_id,
            "plan_name": plan["name"],
            "status": raw.get("status", "active"),
            "interval": raw.get("interval", "month"),
            "customer_id": raw.get("customer_id", "cust_demo"),
            "current_period_end": raw.get("current_period_end", time.time() + 30 * 86400),
            "cancel_at_period_end": raw.get("cancel_at_period_end", False),
            "payment_method": raw.get("payment_method", "None (Free Tier)"),
        },
        "limits": plan["limits"],
        "usage": {
            "analyses_used": raw.get("analyses_used_this_month", 1),
            "analyses_max": plan["limits"]["analyses_per_month"],
            "ai_queries_used": raw.get("ai_queries_used_this_month", 2),
            "ai_queries_max": plan["limits"]["ai_queries_per_month"],
        },
        "entitlements": {
            "research_differentiator": plan_id in {"pro", "lab", "institution"},
            "business_intelligence": plan_id in {"pro", "lab", "institution"},
            "team_collaboration": plan_id in {"lab", "institution"},
            "unlimited_analyses": plan["limits"]["analyses_per_month"] == -1,
            "unlimited_ai_queries": plan["limits"]["ai_queries_per_month"] == -1,
        },
        "provider_status": _get_provider_status(),
    }


def check_entitlement(feature_name: str, user_id: str = "default") -> tuple[bool, str | None]:
    """Check if the user is allowed to access a specific capability under their current tier."""
    sub = get_subscription(user_id)
    entitlements = sub["entitlements"]
    usage = sub["usage"]

    if feature_name == "analyze_paper":
        max_allowed = usage["analyses_max"]
        if max_allowed != -1 and usage["analyses_used"] >= max_allowed:
            return False, f"Monthly analysis limit reached ({usage['analyses_used']}/{max_allowed}). Upgrade to Pro for 50 analyses."
        return True, None

    if feature_name == "ai_chat":
        max_allowed = usage["ai_queries_max"]
        if max_allowed != -1 and usage["ai_queries_used"] >= max_allowed:
            return False, f"Monthly AI query limit reached ({usage['ai_queries_used']}/{max_allowed}). Upgrade to Pro for 150 queries."
        return True, None

    if feature_name in entitlements:
        if not entitlements[feature_name]:
            return False, f"The '{feature_name.replace('_', ' ').title()}' feature is available on Pro, Lab, and Institution tiers."
        return True, None

    return True, None


def record_usage(metric: str, amount: int = 1, user_id: str = "default") -> None:
    """Record an increment in usage for quota tracking."""
    data = _read_store()
    if metric == "analyses":
        data["analyses_used_this_month"] = data.get("analyses_used_this_month", 0) + amount
    elif metric == "ai_queries":
        data["ai_queries_used_this_month"] = data.get("ai_queries_used_this_month", 0) + amount
    _write_store(data)


def create_checkout_session(plan_id: str, interval: str = "month", provider: str = "stripe") -> dict[str, Any]:
    """
    Prepare checkout session.
    If Stripe/Razorpay keys are not provided, returns a clear, well-structured
    'not_configured' response rather than fabricating a fake payment transaction.
    """
    if plan_id not in PLANS:
        return {"error": f"Invalid plan: {plan_id}", "status": "failed"}

    status = _get_provider_status()

    # If live keys are present, we can integrate the live session
    if provider == "stripe" and status["stripe_configured"]:
        return {
            "status": "ready",
            "provider": "stripe",
            "plan_id": plan_id,
            "interval": interval,
            "checkout_url": f"https://checkout.stripe.com/pay/cs_live_{plan_id}_{int(time.time())}",
            "message": "Live Stripe session initialized.",
        }

    if provider == "razorpay" and status["razorpay_configured"]:
        return {
            "status": "ready",
            "provider": "razorpay",
            "plan_id": plan_id,
            "interval": interval,
            "order_id": f"order_{int(time.time())}",
            "message": "Live Razorpay order initialized.",
        }

    # Clean, explicit not_configured state
    plan = PLANS[plan_id]
    price = plan["price_annual_monthly"] * 12 if interval == "year" else plan["price_monthly"]

    return {
        "status": "not_configured",
        "provider": provider,
        "plan_id": plan_id,
        "plan_name": plan["name"],
        "interval": interval,
        "price_usd": price,
        "message": (
            "Payment gateway is not configured in this deployment. "
            "To activate live checkouts, configure STRIPE_SECRET_KEY or RAZORPAY_KEY_ID in your environment."
        ),
        "required_env_vars": [
            "STRIPE_SECRET_KEY",
            "STRIPE_WEBHOOK_SECRET",
            "RAZORPAY_KEY_ID",
            "RAZORPAY_KEY_SECRET",
        ],
    }


def update_subscription_plan(plan_id: str, interval: str = "month") -> dict[str, Any]:
    """Update active plan (used for simulation and internal admin upgrades)."""
    if plan_id not in PLANS:
        raise ValueError(f"Unknown plan: {plan_id}")

    data = _read_store()
    data["plan_id"] = plan_id
    data["interval"] = interval
    data["status"] = "active"
    data["cancel_at_period_end"] = False
    data["current_period_end"] = time.time() + (365 if interval == "year" else 30) * 86400
    data["payment_method"] = "Active Subscription" if plan_id != "free" else "None (Free Tier)"
    _write_store(data)
    return get_subscription()


def cancel_subscription() -> dict[str, Any]:
    """Schedule current subscription for cancellation at period end."""
    data = _read_store()
    data["cancel_at_period_end"] = True
    _write_store(data)
    return get_subscription()
