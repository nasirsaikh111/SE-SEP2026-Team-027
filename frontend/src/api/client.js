// Small fetch wrapper for the Sangam Django API (JWT in localStorage, base /api/v1 via the Vite proxy)
const BASE = import.meta.env.VITE_API_BASE || '/api/v1';
const TOKEN_KEY = 'sangam_access';

export function getToken() {
  try { return localStorage.getItem(TOKEN_KEY); } catch { return null; }
}

export function setToken(token) {
  try {
    if (token) localStorage.setItem(TOKEN_KEY, token);
    else localStorage.removeItem(TOKEN_KEY);
  } catch { /* storage blocked: stay logged in for this tab only */ }
}

export class ApiError extends Error {
  constructor(status, body) {
    super((body && (body.detail || JSON.stringify(body))) || `HTTP ${status}`);
    this.status = status;
    this.body = body;
  }
}

export async function api(path, { method = 'GET', body, auth = true } = {}) {
  const headers = { Accept: 'application/json' };
  if (body !== undefined) headers['Content-Type'] = 'application/json';
  const token = getToken();
  if (auth && token) headers.Authorization = `Bearer ${token}`;
  const res = await fetch(BASE + path, { method, headers, body: body === undefined ? undefined : JSON.stringify(body) });
  let data = null;
  try { data = await res.json(); } catch { data = null; }
  // 503 from the summary endpoint still carries a usable fallback draft
  if (!res.ok && !(res.status === 503 && data && data.fallback)) throw new ApiError(res.status, data);
  return data;
}

// Convenience calls for the AI features
export const Sangam = {
  login: (email, password) => api('/auth/token/', { method: 'POST', body: { email, password }, auth: false }),
  me: () => api('/auth/me/'),
  health: () => api('/ai/health/'),
  insights: () => api('/admin/insights/'),
  atRisk: (minLevel = 'MEDIUM') => api(`/admin/insights/at-risk/?min_level=${minLevel}`),
  requests: () => api('/requests/'),
  suggestions: (id, k = 5) => api(`/requests/${id}/suggestions/?k=${k}`),
  priority: (id) => api(`/requests/${id}/priority/`),
  overridePriority: (id, priority, reason) =>
    api(`/requests/${id}/priority/`, { method: 'PATCH', body: { override_priority: priority, override_reason: reason } }),
  mentorships: () => api('/mentorships/'),
  meetings: (pairId) => api(`/mentorships/${pairId}/meetings/`),
  summarise: (pairId, meetingId, notes) =>
    api(`/mentorships/${pairId}/meetings/${meetingId}/summary/`, { method: 'POST', body: { notes } }),
  confirmSummary: (pairId, meetingId, payload) =>
    api(`/mentorships/${pairId}/meetings/${meetingId}/summary/confirm/`, { method: 'POST', body: payload }),
  chat: (message) => api('/assistant/chat/', { method: 'POST', body: { message } }),
};
