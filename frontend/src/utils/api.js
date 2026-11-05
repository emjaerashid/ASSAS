// Same-origin by default: in production Django serves the app and /api from
// one domain, and in development Vite proxies /api and /media to Django (see
// vite.config.js). VITE_API_BASE overrides it for a separately hosted API.
const API_BASE = import.meta.env.VITE_API_BASE || '/api';
const SERVER_BASE = API_BASE.replace(/\/api\/?$/, '');

// Uploaded file fields (e.g. Timetable.file) come back from the API as
// paths relative to the Django server (e.g. "/media/timetables/x.pdf").
// Used directly as a href/src, they'd resolve against the frontend's own
// origin instead of the backend's, so 404. Prefix them with SERVER_BASE.
export function resolveMediaUrl(path) {
  if (!path || /^https?:\/\//.test(path)) return path;
  return `${SERVER_BASE}${path}`;
}

function getCookie(name) {
  const value = `; ${document.cookie}`;
  const parts = value.split(`; ${name}=`);
  if (parts.length === 2) return parts.pop().split(';').shift();
  return null;
}

// DRF returns { error: "..." } or { detail: "..." } for view-level errors,
// but serializer validation failures (e.g. is_valid(raise_exception=True))
// come back as { field_name: ["message", ...], ... } instead - without this,
// those fall through to a generic, unhelpful "Request failed".
function extractErrorMessage(data) {
  if (!data || typeof data !== 'object') return 'Request failed';
  if (data.error) return data.error;
  if (data.detail) return data.detail;

  const messages = Object.entries(data).flatMap(([field, value]) => {
    const texts = Array.isArray(value) ? value : [value];
    return texts.map((text) => (field === 'non_field_errors' ? text : `${field}: ${text}`));
  });

  return messages.length ? messages.join(' ') : 'Request failed';
}

async function request(path, options = {}) {
  const url = `${API_BASE}${path}`;
  const config = {
    credentials: 'include',
    headers: {
      'X-CSRFToken': getCookie('csrftoken'),
      ...options.headers,
    },
    ...options,
  };

  if (!(options.body instanceof FormData)) {
    config.headers['Content-Type'] = 'application/json';
  }

  const response = await fetch(url, config);

  if (response.status === 204) return null;

  const data = await response.json().catch(() => null);

  if (!response.ok) {
    throw new Error(extractErrorMessage(data));
  }

  return data;
}

const api = {
  get: (path) => request(path),
  post: (path, body) =>
    request(path, {
      method: 'POST',
      body: body instanceof FormData ? body : JSON.stringify(body),
    }),
  put: (path, body) =>
    request(path, {
      method: 'PUT',
      body: body instanceof FormData ? body : JSON.stringify(body),
    }),
  delete: (path) => request(path, { method: 'DELETE' }),
};

export default api;
