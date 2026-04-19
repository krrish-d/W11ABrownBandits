import axios from "axios";

const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";

const client = axios.create({
  baseURL: API_BASE,
  headers: {
    "Content-Type": "application/json",
  },
});

client.interceptors.response.use(
  (response) => response,
  async (error) => {
    const res = error.response;
    const data = res?.data;
    if (res?.status >= 400 && data instanceof Blob) {
      try {
        const text = await data.text();
        const trimmed = text.trim();
        if (trimmed.startsWith("{")) {
          res.data = JSON.parse(trimmed);
        }
      } catch {
        /* keep blob */
      }
    }
    return Promise.reject(error);
  }
);

export function formatApiError(error) {
  return (
    error?.response?.data?.detail ||
    error?.response?.data?.message ||
    error?.message ||
    "Something went wrong"
  );
}

export function createBlobUrl(data, contentType = "text/plain") {
  const blob = data instanceof Blob ? data : new Blob([data], { type: contentType });
  return URL.createObjectURL(blob);
}

export default client;
