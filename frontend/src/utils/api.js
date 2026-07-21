const API_BASE = 'http://localhost:8000/api';
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
    const message = data?.error || data?.detail || 'Request failed';
    throw new Error(message);
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
      body: JSON.stringify(body),
    }),
  delete: (path) => request(path, { method: 'DELETE' }),
};

export default api;
