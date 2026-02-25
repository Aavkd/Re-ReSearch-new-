import axios, { AxiosError } from "axios";

/**
 * Shared axios instance.
 *
 * `baseURL` is read from the Vite env variable so that:
 *  - Development: `http://localhost:8000` (direct, or proxied via `/api`)
 *  - Production build: override via `VITE_API_BASE_URL`
 */
export const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL as string,
  headers: {
    "Content-Type": "application/json",
  },
});

/**
 * Response interceptor — normalise HTTP error responses into plain `Error`
 * objects with a human-readable message.
 *
 * FastAPI returns `{ "detail": "..." }` for validation and application errors,
 * so we extract that when available.
 */
apiClient.interceptors.response.use(
  (response) => response,
  (error: AxiosError<{ detail?: string }>) => {
    const detail = error.response?.data?.detail;
    const status = error.response?.status;

    let message: string;
    if (detail) {
      message = String(detail);
    } else if (status) {
      message = `Request failed with status ${status}`;
    } else {
      message = error.message ?? "Network Error";
    }

    return Promise.reject(new Error(message));
  }
);
