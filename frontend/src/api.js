const API_BASE = "/api";

async function request(path, options = {}) {
  const resp = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!resp.ok) {
    let detail = resp.statusText;
    try {
      const body = await resp.json();
      detail = body.detail || detail;
    } catch (_e) {
      // response wasn't JSON, keep statusText
    }
    throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
  }
  return resp.json();
}

export function analyzeRepo(repoUrl) {
  return request("/analyze", {
    method: "POST",
    body: JSON.stringify({ repo_url: repoUrl }),
  });
}

export function fetchHistory(limit = 50) {
  return request(`/history?limit=${limit}`);
}

export function fetchHistoryItem(id) {
  return request(`/history/${id}`);
}

export function deleteHistoryItem(id) {
  return request(`/history/${id}`, { method: "DELETE" });
}

export function runWhatIf(id, overrides) {
  return request(`/whatif/${id}`, {
    method: "POST",
    body: JSON.stringify({ overrides }),
  });
}

export function reportUrl(id) {
  return `${API_BASE}/report/${id}`;
}
