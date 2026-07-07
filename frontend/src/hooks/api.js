/**
 * API client hook for communicating with the Node.js gateway.
 */
const API_BASE = import.meta.env.VITE_API_URL || '/api';

let authToken = null;

export function setToken(token) {
  authToken = token;
}

export function getToken() {
  return authToken;
}

async function request(path, options = {}) {
  const headers = {
    'Content-Type': 'application/json',
    ...(authToken ? { Authorization: `Bearer ${authToken}` } : {}),
    ...options.headers,
  };

  const res = await fetch(`${API_BASE}${path}`, { ...options, headers });

  if (!res.ok) {
    const body = await res.json().catch(() => ({ error: res.statusText }));
    throw new Error(body.error || body.detail || `Request failed: ${res.status}`);
  }

  return res.json();
}

// Auth
export const loginAsGuest = () => request('/auth/guest', { method: 'POST' });
export const login = (username, password) =>
  request('/auth/login', { method: 'POST', body: JSON.stringify({ username, password }) });
export const register = (username, password) =>
  request('/auth/register', { method: 'POST', body: JSON.stringify({ username, password }) });

// Sessions
export const createSession = () => request('/sessions', { method: 'POST' });
export const getSession = (id) => request(`/sessions/${id}`);

// Queries
export const sendQuery = (query, sessionId) =>
  request('/query', {
    method: 'POST',
    body: JSON.stringify({ query, sessionId }),
  });

// Schema
export const getSchema = () => request('/schema');

// DB Management
export const connectDb = (dbPath) =>
  request('/connect-db', {
    method: 'POST',
    body: JSON.stringify({ db_path: dbPath }),
  });

export const uploadDb = async (file) => {
  const formData = new FormData();
  formData.append('file', file);

  const res = await fetch(`${API_BASE}/upload-db`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${authToken}` },
    body: formData,
  });

  if (!res.ok) {
    const body = await res.json().catch(() => ({ error: 'Upload failed' }));
    throw new Error(body.error || body.detail || 'Upload failed');
  }

  return res.json();
};

// Sample DB
export const useSampleDb = () => request('/use-sample', { method: 'POST' });

// Health
export const healthCheck = () => fetch(`${API_BASE}/health`).then((r) => r.json());
