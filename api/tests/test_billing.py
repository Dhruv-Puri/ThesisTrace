import importlib.util
import unittest
from unittest.mock import patch

from api.pipeline import billing

HAS_FASTAPI = bool(
    importlib.util.find_spec("fastapi") and importlib.util.find_spec("httpx")
)


class BillingModuleTests(unittest.TestCase):
    def test_get_plans_returns_all_four_tiers(self):
        result = billing.get_plans()
        plans = result["plans"]
        plan_ids = [p["id"] for p in plans]
        self.assertIn("free", plan_ids)
        self.assertIn("pro", plan_ids)
        self.assertIn("lab", plan_ids)
        self.assertIn("institution", plan_ids)

        pro = next(p for p in plans if p["id"] == "pro")
        self.assertTrue(pro["highlighted"])
        self.assertGreater(pro["annual_discount_percent"], 0)
        self.assertEqual(pro["price_monthly"], 19)
        self.assertEqual(pro["price_annual_monthly"], 15)

    def test_get_subscription_defaults_to_free(self):
        with patch("api.pipeline.billing._read_store", return_value={"plan_id": "free"}):
            sub = billing.get_subscription("test-user")
        self.assertEqual(sub["subscription"]["plan_id"], "free")
        self.assertEqual(sub["subscription"]["status"], "active")
        self.assertFalse(sub["entitlements"]["research_differentiator"])
        self.assertFalse(sub["entitlements"]["team_collaboration"])

    def test_entitlements_for_pro_tier(self):
        with patch("api.pipeline.billing._read_store", return_value={"plan_id": "pro"}):
            sub = billing.get_subscription("test-user")
        self.assertEqual(sub["subscription"]["plan_id"], "pro")
        self.assertTrue(sub["entitlements"]["research_differentiator"])
        self.assertTrue(sub["entitlements"]["business_intelligence"])
        self.assertFalse(sub["entitlements"]["team_collaboration"])

    def test_check_entitlement_enforces_limits(self):
        with patch("api.pipeline.billing._read_store", return_value={
            "plan_id": "free",
            "analyses_used_this_month": 3,
        }):
            allowed, reason = billing.check_entitlement("analyze_paper")
            self.assertFalse(allowed)
            self.assertIn("limit reached", reason.lower())

        with patch("api.pipeline.billing._read_store", return_value={
            "plan_id": "free",
            "analyses_used_this_month": 1,
        }):
            allowed, reason = billing.check_entitlement("analyze_paper")
            self.assertTrue(allowed)
            self.assertIsNone(reason)

    def test_checkout_when_unconfigured_provides_clear_instructions(self):
        with patch.dict("os.environ", {"STRIPE_SECRET_KEY": "", "RAZORPAY_KEY_ID": ""}, clear=True):
            checkout = billing.create_checkout_session("pro", "year", provider="stripe")
        self.assertEqual(checkout["status"], "not_configured")
        self.assertIn("STRIPE_SECRET_KEY", checkout["required_env_vars"])
        self.assertIn("Payment gateway is not configured", checkout["message"])

    def test_checkout_when_configured(self):
        with patch.dict("os.environ", {"STRIPE_SECRET_KEY": "sk_test_123"}):
            checkout = billing.create_checkout_session("pro", "month", provider="stripe")
        self.assertEqual(checkout["status"], "ready")
        self.assertEqual(checkout["provider"], "stripe")
        self.assertIn("checkout.stripe.com", checkout["checkout_url"])


@unittest.skipUnless(HAS_FASTAPI, "FastAPI / TestClient is required for route tests")
class BillingApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from fastapi.testclient import TestClient
        from api.main import app

        cls.client = TestClient(app)

    def test_get_plans_endpoint(self):
        response = self.client.get("/api/billing/plans")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(len(body["plans"]), 4)
        self.assertTrue(body["faq"])

    def test_get_subscription_endpoint(self):
        response = self.client.get("/api/billing/subscription")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertIn("subscription", body)
        self.assertIn("limits", body)
        self.assertIn("usage", body)

    def test_checkout_endpoint(self):
        response = self.client.post("/api/billing/checkout", json={
            "plan_id": "pro",
            "interval": "month",
            "provider": "stripe",
        })
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertIn(body["status"], {"ready", "not_configured"})

    def test_update_plan_endpoint(self):
        response = self.client.post("/api/billing/plan", json={
            "plan_id": "pro",
            "interval": "year",
        })
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["subscription"]["plan_id"], "pro")

        # Roll back to free
        self.client.post("/api/billing/plan", json={
            "plan_id": "free",
            "interval": "month",
        })
