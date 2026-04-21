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
  RecurringRule,
  AuditLog,
  SendPayload,
  Template,
  User,
} from "./types";

// In local/proxy mode use Next.js /api rewrites.
// In deployed static/frontend-only mode set NEXT_PUBLIC_API_BASE_URL to your backend URL root.
// This backend exposes auth/clients/payments at root paths, so "/v2" would 404 those endpoints.
const configuredPublicApiBase = process.env.NEXT_PUBLIC_API_BASE_URL?.trim();
const normalizedConfiguredBase = configuredPublicApiBase?.replace(/\/+$/, "");
export const API_BASE = normalizedConfiguredBase?.replace(/\/v2$/, "") || "/api";
const TOKEN_KEY = "invoiceflow_token";
const TOKEN_COOKIE_MAX_AGE_SECONDS = 60 * 60 * 24 * 7; // 7 days

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
    const responseData = error.response?.data;
    const detail =
      typeof responseData === "object" && responseData && "detail" in responseData
        ? (responseData as { detail?: unknown }).detail
        : undefined;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail)) {
      const validationMessages = detail
        .map((item) => {
          if (typeof item === "string") return item;
          if (typeof item === "object" && item && "msg" in item) {
            return String((item as { msg?: unknown }).msg ?? "");
          }
          return "";
        })
        .filter(Boolean);
      if (validationMessages.length) return validationMessages.join(", ");
    }
    if (detail && typeof detail === "object") {
      return "Request failed due to invalid input.";
    }

    // Proxy/backend failures may surface as 500 from Next.js rewrites.
    if (error.response?.status === 500) {
      return "Could not reach the backend API. Check your deployed API URL or local FastAPI server.";
    }

    if (!error.response) {
      return "Network error: backend API is unreachable.";
    }

    return error.message;
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
  document.cookie = `${TOKEN_KEY}=${encodeURIComponent(token)}; path=/; max-age=${TOKEN_COOKIE_MAX_AGE_SECONDS}; samesite=lax`;
}

export function clearStoredToken() {
  if (typeof window === "undefined") return;
  window.localStorage.removeItem(TOKEN_KEY);
  document.cookie = `${TOKEN_KEY}=; path=/; max-age=0; samesite=lax`;
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

export async function createTemplate(payload: {
  name: string;
  logo_url?: string;
  primary_colour?: string;
  secondary_colour?: string;
  footer_text?: string;
  payment_terms_text?: string;
  bank_details?: string;
  is_default?: boolean;
}) {
  const { data } = await client.post<Template>("/templates", payload);
  return data;
}

export async function fetchRecurringRules() {
  const { data } = await client.get<RecurringRule[]>("/recurring");
  return data;
}

export async function createRecurringRule(payload: {
  name: string;
  frequency: string;
  next_run_date: string;
  end_date?: string;
  invoice_template: {
    seller_name: string;
    seller_address: string;
    seller_email: string;
    buyer_name: string;
    buyer_address: string;
    buyer_email: string;
    currency: string;
    due_date: string;
    notes?: string;
    items: Array<{
      item_number: string;
      description: string;
      quantity: number;
      unit_price: number;
      tax_rate: number;
    }>;
  };
}) {
  const { data } = await client.post<RecurringRule>("/recurring", payload);
  return data;
}

export async function deleteRecurringRule(recurringId: string) {
  const { data } = await client.delete(`/recurring/${recurringId}`);
  return data;
}

export async function fetchAuditLogs(params?: {
  entity_type?: string;
  action?: string;
  limit?: number;
}) {
  const { data } = await client.get<AuditLog[]>("/audit", { params });
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

export async function parseInvoiceFile(file: File): Promise<Record<string, unknown>> {
  const formData = new FormData();
  formData.append("file", file);
  const { data } = await client.post<Record<string, unknown>>("/invoice/parse-file", formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return data;
}
