const JSON_HEADERS = { Accept: "application/json" };

async function readJson(response) {
  const payload = await response.json().catch(() => null);
  if (!response.ok) {
    const message =
      payload?.error?.message ||
      payload?.detail?.message ||
      `Request failed (HTTP ${response.status}).`;
    throw new Error(message);
  }
  return payload;
}

export async function uploadPaper(file) {
  const form = new FormData();
  form.append("file", file);
  const response = await fetch("/api/jobs", {
    method: "POST",
    body: form,
    headers: { Accept: "application/json" },
  });
  return readJson(response);
}

export async function getJob(jobId) {
  const response = await fetch(`/api/jobs/${encodeURIComponent(jobId)}`, {
    headers: JSON_HEADERS,
  });
  return readJson(response);
}

export async function getConfig() {
  const response = await fetch("/api/config", { headers: JSON_HEADERS });
  return readJson(response);
}

export function reportUrl(jobId) {
  return `/api/jobs/${encodeURIComponent(jobId)}/report?format=md`;
}

export async function askPaper(jobId, question, history = []) {
  const response = await fetch(`/api/jobs/${encodeURIComponent(jobId)}/chat`, {
    method: "POST",
    headers: { ...JSON_HEADERS, "Content-Type": "application/json" },
    body: JSON.stringify({ question, history }),
  });
  return readJson(response);
}

export async function deleteJob(jobId) {
  const response = await fetch(`/api/jobs/${encodeURIComponent(jobId)}`, {
    method: "DELETE",
    headers: JSON_HEADERS,
  });
  return readJson(response);
}

export async function getAudit(jobId) {
  const response = await fetch(`/api/jobs/${encodeURIComponent(jobId)}/audit`, {
    headers: JSON_HEADERS,
  });
  return readJson(response);
}

export async function createPortfolio(jobIds, name = "") {
  const response = await fetch("/api/portfolios", {
    method: "POST",
    headers: { ...JSON_HEADERS, "Content-Type": "application/json" },
    body: JSON.stringify({ job_ids: jobIds, name: name || null }),
  });
  return readJson(response);
}

export async function getPortfolio(portfolioId) {
  const response = await fetch(`/api/portfolios/${encodeURIComponent(portfolioId)}`, {
    headers: JSON_HEADERS,
  });
  return readJson(response);
}

export async function differentiatePaper(jobId, limit = 8) {
  const params = new URLSearchParams({ limit: String(limit) });
  const response = await fetch(`/api/jobs/${encodeURIComponent(jobId)}/differentiate?${params}`, {
    method: "POST",
    headers: JSON_HEADERS,
  });
  return readJson(response);
}

export async function getBusinessIntelligence(jobId) {
  const response = await fetch(`/api/jobs/${encodeURIComponent(jobId)}/business-intelligence`, {
    method: "POST",
    headers: JSON_HEADERS,
  });
  return readJson(response);
}

export async function getBillingPlans() {
  const response = await fetch("/api/billing/plans", { headers: JSON_HEADERS });
  return readJson(response);
}

export async function getBillingSubscription() {
  const response = await fetch("/api/billing/subscription", { headers: JSON_HEADERS });
  return readJson(response);
}

export async function createCheckoutSession(planId, interval = "month", provider = "stripe") {
  const response = await fetch("/api/billing/checkout", {
    method: "POST",
    headers: { ...JSON_HEADERS, "Content-Type": "application/json" },
    body: JSON.stringify({ plan_id: planId, interval, provider }),
  });
  return readJson(response);
}

export async function updatePlan(planId, interval = "month") {
  const response = await fetch("/api/billing/plan", {
    method: "POST",
    headers: { ...JSON_HEADERS, "Content-Type": "application/json" },
    body: JSON.stringify({ plan_id: planId, interval }),
  });
  return readJson(response);
}

export async function cancelSubscription() {
  const response = await fetch("/api/billing/cancel", {
    method: "POST",
    headers: JSON_HEADERS,
  });
  return readJson(response);
}
