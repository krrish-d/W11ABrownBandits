import axios from "axios";
import type {
  AuthResponse,
  Client,
  CommunicationLog,
  DashboardKpis,
  DashboardNeedsAttention,
  DashboardTopClients,
  DashboardTrendPoint,
  Invoice,
  InvoicePaymentSummary,
  Payment,
  SendPayload,
  Template,
  User,
} from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "http://127.0.0.1:8000";
const TOKEN_KEY = "invoiceflow_token";

const client = axios.create({
  baseURL: API_BASE,
  headers: { "Content-Type": "application/json" },
});

client.interceptors.request.use((config) => {
  if (typeof window !== "undefined") {
    const token = window.localStorage.getItem(TOKEN_KEY);
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
  }
  return config;
});

export function getApiError(error: unknown) {
  if (axios.isAxiosError(error)) {
    return (error.response?.data as { detail?: string })?.detail || error.message;
  }
  return "Something went wrong.";
}

export function getStoredToken() {
  if (typeof window === "undefined") return "";
  return window.localStorage.getItem(TOKEN_KEY) || "";
}

export function setStoredToken(token: string) {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(TOKEN_KEY, token);
}

export function clearStoredToken() {
  if (typeof window === "undefined") return;
  window.localStorage.removeItem(TOKEN_KEY);
}

export async function login(email: string, password: string) {
  const payload = new URLSearchParams();
  payload.set("username", email);
  payload.set("password", password);
  const { data } = await client.post<AuthResponse>("/auth/login", payload.toString(), {
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
  });
  setStoredToken(data.access_token);
  return data;
}

export async function signup(payload: { email: string; password: string; full_name?: string; role?: string }) {
  const { data } = await client.post<AuthResponse>("/auth/signup", payload);
  setStoredToken(data.access_token);
  return data;
}

export async function fetchMe() {
  const { data } = await client.get<User>("/auth/me");
  return data;
}

export async function fetchInvoices(params?: {
  status?: string;
  search?: string;
  date_from?: string;
  date_to?: string;
  min_amount?: number;
  max_amount?: number;
  sort_by?: string;
  sort_order?: "asc" | "desc";
  page?: number;
  page_size?: number;
}) {
  const { data } = await client.get<Invoice[]>("/invoice/list", { params });
  return data;
}

export async function fetchInvoice(id: string, format = "json") {
  const { data } = await client.get<Invoice | string>(`/invoice/fetch/${id}?format=${format}`, {
    responseType: format === "json" ? "json" : "text",
  });
  return data;
}

export async function createInvoice(payload: Partial<Invoice>) {
  const { data } = await client.post<Invoice>("/invoice/create", payload);
  return data;
}

export async function updateInvoice(id: string, payload: Partial<Invoice>) {
  const { data } = await client.put<Invoice>(`/invoice/update/${id}`, payload);
  return data;
}

export async function removeInvoice(id: string) {
  const { data } = await client.delete(`/invoice/delete/${id}`);
  return data;
}

export async function sendInvoiceEmail(payload: SendPayload) {
  const { data } = await client.post("/communicate/send", payload);
  return data;
}

export async function sendInvoiceWithImportLink(invoiceId: string, recipient_email: string) {
  const { data } = await client.post(`/communicate/send-invoice/${invoiceId}`, null, {
    params: { recipient_email },
  });
  return data as {
    message: string;
    invoice_id: string;
    recipient_email: string;
    import_url: string;
    token_expires_at: string;
  };
}

export async function sendInvoiceReminder(invoiceId: string) {
  const { data } = await client.post(`/communicate/remind/${invoiceId}`);
  return data;
}

export async function fetchCommunicationLogs() {
  const { data } = await client.get<CommunicationLog[]>("/communicate/logs");
  return data;
}

export async function updateInvoiceStatus(invoiceId: string, status: string) {
  const { data } = await client.put<Invoice>(`/invoice/${invoiceId}/status`, null, {
    params: { status },
  });
  return data;
}

export async function fetchInvoicePaymentSummary(invoiceId: string) {
  const { data } = await client.get<InvoicePaymentSummary>(`/payments/invoice/${invoiceId}`);
  return data;
}

export async function recordPayment(payload: {
  invoice_id: string;
  amount: number;
  method: string;
  reference?: string;
  payment_date: string;
  notes?: string;
}) {
  const { data } = await client.post<Payment>("/payments", payload);
  return data;
}

export async function fetchClients(search?: string) {
  const { data } = await client.get<Client[]>("/clients", {
    params: search ? { search } : undefined,
  });
  return data;
}

export async function createClient(payload: Partial<Client>) {
  const { data } = await client.post<Client>("/clients", payload);
  return data;
}

export async function fetchTemplates() {
  const { data } = await client.get<Template[]>("/templates");
  return data;
}

export async function fetchDashboardKpis() {
  const { data } = await client.get<DashboardKpis>("/dashboard/kpis");
  return data;
}

export async function fetchDashboardTrend(months = 12) {
  const { data } = await client.get<{ monthly: DashboardTrendPoint[] }>("/dashboard/trend", {
    params: { months },
  });
  return data;
}

export async function fetchDashboardNeedsAttention() {
  const { data } = await client.get<DashboardNeedsAttention>("/dashboard/needs-attention");
  return data;
}

export async function fetchDashboardTopClients(limit = 6) {
  const { data } = await client.get<DashboardTopClients>("/dashboard/top-clients", {
    params: { limit },
  });
  return data;
}
