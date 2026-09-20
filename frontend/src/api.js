// One place for every call to the backend. Pages never use fetch() directly.
const BASE_URL = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";
const TOKEN_KEY = "api-generator-token";

export const getToken = () => localStorage.getItem(TOKEN_KEY);
export const setToken = (token) => localStorage.setItem(TOKEN_KEY, token);
export const clearToken = () => localStorage.removeItem(TOKEN_KEY);

export class ApiError extends Error {
  constructor(status, message, data) {
    super(message);
    this.status = status;
    this.data = data; // the raw error body, e.g. the agent's clarification questions
  }
}

// FastAPI sends errors in three shapes: a string, a list (validation) or an object.
function readableMessage(data, status) {
  const detail = data && data.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail.map((d) => `${d.loc[d.loc.length - 1]}: ${d.msg}`).join(". ");
  }
  if (detail && detail.message) {
    const extra = detail.errors || detail.questions || [];
    return [detail.message, ...extra].join(" ");
  }
  return `The server answered with an error (${status}).`;
}

export async function api(path, { method = "GET", body } = {}) {
  const headers = {};
  if (body !== undefined) headers["Content-Type"] = "application/json";
  const token = getToken();
  if (token) headers["Authorization"] = `Bearer ${token}`;

  let response;
  try {
    response = await fetch(BASE_URL + path, {
      method,
      headers,
      body: body !== undefined ? JSON.stringify(body) : undefined,
    });
  } catch {
    throw new ApiError(0, "Cannot reach the server. Check that the backend is running on port 8000.");
  }

  if (response.status === 204) return null;
  const data = await response.json().catch(() => null);
  if (!response.ok) {
    if (response.status === 401 && token) {
      clearToken(); // the login expired: tell the app so it can show the login page
      window.dispatchEvent(new Event("auth:expired"));
    }
    throw new ApiError(response.status, readableMessage(data, response.status), data);
  }
  return data;
}

// Downloads a file that needs the login token (a normal link cannot send the token).
export async function download(path, filename) {
  const token = getToken();
  let response;
  try {
    response = await fetch(BASE_URL + path, { headers: token ? { Authorization: `Bearer ${token}` } : {} });
  } catch {
    throw new ApiError(0, "Cannot reach the server. Check that the backend is running on port 8000.");
  }
  if (!response.ok) {
    const data = await response.json().catch(() => null);
    throw new ApiError(response.status, readableMessage(data, response.status), data);
  }
  const url = URL.createObjectURL(await response.blob());
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}