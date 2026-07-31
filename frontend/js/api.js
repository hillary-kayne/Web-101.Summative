const TOKEN_KEY = "rethread_token";
const USERNAME_KEY = "rethread_username";

const escapeHtml = (s) =>
  String(s ?? "").replace(/[&<>"']/g, (c) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  }[c]));

const Auth = {
  getToken: () => localStorage.getItem(TOKEN_KEY),
  getUsername: () => localStorage.getItem(USERNAME_KEY),
  setSession: (token, username) => {
    localStorage.setItem(TOKEN_KEY, token);
    localStorage.setItem(USERNAME_KEY, username);
  },
  clearSession: () => {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USERNAME_KEY);
  },
  isLoggedIn: () => !!localStorage.getItem(TOKEN_KEY),
};

async function apiRequest(path, { method = "GET", body, auth = false } = {}) {
  const headers = { "Content-Type": "application/json" };
  if (auth) {
    const token = Auth.getToken();
    if (!token) {
      window.location.href = "/auth.html";
      throw new Error("Not authenticated");
    }
    headers["Authorization"] = `Bearer ${token}`;
  }

  let res;
  try {
    res = await fetch(path, {
      method,
      headers,
      body: body ? JSON.stringify(body) : undefined,
    });
  } catch (networkErr) {
    throw new Error("Network error. Check your connection and try again.");
  }

  if (res.status === 204) return null;

  let data = null;
  try {
    data = await res.json();
  } catch (e) {
    /* no body */
  }

  if (res.status === 401 && auth) {
    Auth.clearSession();
    window.location.href = "/auth.html";
    throw new Error("Session expired");
  }

  if (!res.ok) {
    throw new Error((data && data.error) || `Request failed (${res.status})`);
  }

  return data;
}

const Api = {
  signup: (username, password) => apiRequest("/api/auth/signup", { method: "POST", body: { username, password } }),
  login: (username, password) => apiRequest("/api/auth/login", { method: "POST", body: { username, password } }),

  geocode: (q) => apiRequest(`/api/locator/geocode?q=${encodeURIComponent(q)}`),
  search: (params) => apiRequest(`/api/locator/search?${new URLSearchParams(params).toString()}`),

  listEntries: (params) => apiRequest(`/api/tracker/entries?${new URLSearchParams(params).toString()}`, { auth: true }),
  createEntry: (entry) => apiRequest("/api/tracker/entries", { method: "POST", body: entry, auth: true }),
  deleteEntry: (id) => apiRequest(`/api/tracker/entries/${id}`, { method: "DELETE", auth: true }),
  summary: () => apiRequest("/api/tracker/summary", { auth: true }),
};
