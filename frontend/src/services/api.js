// One shared Axios instance for the whole app.
//
// Token strategy:
//  - The short-lived ACCESS token lives only in this JS variable (memory).
//    It is lost on page reload, and that is fine: we get a new one from /auth/refresh.
//  - The long-lived REFRESH token is an HttpOnly cookie that JavaScript cannot read.
import axios from "axios";

export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api/v1";

let accessToken = null;
let onSessionExpired = () => {};

export const setAccessToken = (token) => {
  accessToken = token;
};
export const setSessionExpiredHandler = (handler) => {
  onSessionExpired = handler;
};

export const api = axios.create({
  baseURL: API_BASE_URL,
  withCredentials: true, // lets the browser send/receive the refresh cookie
  headers: { "Content-Type": "application/json" },
});

api.interceptors.request.use((config) => {
  if (accessToken) config.headers.Authorization = `Bearer ${accessToken}`;
  return config;
});

// If several requests fail at once, they all wait for ONE refresh call.
// (The refresh token is rotated on every use, so two parallel refreshes would clash.)
let refreshPromise = null;

export function refreshAccessToken() {
  if (!refreshPromise) {
    refreshPromise = axios
      .post(`${API_BASE_URL}/auth/refresh`, null, { withCredentials: true })
      .then((response) => {
        setAccessToken(response.data.data.access_token);
        return response.data.data;
      })
      .finally(() => {
        refreshPromise = null;
      });
  }
  return refreshPromise;
}

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const original = error.config;
    const status = error.response?.status;
    const isAuthRoute = original?.url?.startsWith("/auth/");

    // Access token expired -> refresh once, then repeat the original request.
    if (status === 401 && original && !original._retried && !isAuthRoute) {
      original._retried = true;
      try {
        const data = await refreshAccessToken();
        original.headers.Authorization = `Bearer ${data.access_token}`;
        return api(original);
      } catch {
        setAccessToken(null);
        onSessionExpired();
      }
    }
    return Promise.reject(error);
  }
);

/** Turn any Axios error into a message that is safe to show the user. */
export function getErrorMessage(error) {
  const apiError = error.response?.data?.error;
  if (apiError) {
    if (Array.isArray(apiError.details) && apiError.details.length > 0) {
      return apiError.details.map((d) => (d.field ? `${d.field}: ${d.message}` : d.message)).join(" • ");
    }
    return apiError.message;
  }
  if (error.code === "ERR_NETWORK") return "Cannot reach the server. Is the backend running?";
  return "Something went wrong. Please try again.";
}

export const getErrorCode = (error) => error.response?.data?.error?.code;
