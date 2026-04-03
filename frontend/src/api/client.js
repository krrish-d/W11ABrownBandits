import axios from "axios";

const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";

const client = axios.create({
  baseURL: API_BASE,
  headers: {
    "Content-Type": "application/json",
  },
});

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
