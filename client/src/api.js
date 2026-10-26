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
