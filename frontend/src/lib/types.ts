export type LineItem = {
  item_id?: string;
  item_number?: string;
  description: string;
  quantity: number;
  unit_price: number;
  tax_rate: number;
  line_total?: number;
};

export type Invoice = {
  invoice_id: string;
  invoice_number: string;
  status: string;
  seller_name?: string;
  seller_address?: string;
  seller_email?: string;
  buyer_name?: string;
  buyer_address?: string;
  buyer_email?: string;
  client_name: string;
  client_email: string;
  currency: string;
  issue_date?: string | null;
  due_date: string;
  notes?: string | null;
  subtotal: number;
  tax_total: number;
  grand_total: number;
  items: LineItem[];
};

export type SendPayload = {
  invoice_id: string;
  recipient_email: string;
  invoice_xml: string;
  sender_name?: string;
  subject?: string;
  message_body?: string;
};

export type CommunicationLog = {
  log_id?: string;
  invoice_id: string;
  recipient_email: string;
  delivery_status?: string;
  timestamp?: string;
  sent_at?: string;
};

export type User = {
  user_id: string;
  email: string;
  full_name?: string | null;
  role: "admin" | "accountant" | "viewer";
  is_active: boolean;
  created_at: string;
};

export type AuthResponse = {
  access_token: string;
  token_type: string;
  user: User;
};

export type Client = {
  client_id: string;
  owner_id?: string | null;
  name: string;
  email: string;
  address?: string | null;
  tax_id?: string | null;
  currency: string;
  payment_terms: number;
  notes?: string | null;
  created_at: string;
};

export type Payment = {
  payment_id: string;
  invoice_id: string;
  amount: number;
  method: string;
  reference?: string | null;
  payment_date: string;
  notes?: string | null;
  created_at: string;
};

export type InvoicePaymentSummary = {
  invoice_id: string;
  grand_total: number;
  total_paid: number;
  outstanding_balance: number;
  payments: Payment[];
};

export type Template = {
  template_id: string;
  owner_id?: string | null;
  name: string;
  logo_url?: string | null;
  primary_colour: string;
  secondary_colour: string;
  footer_text?: string | null;
  payment_terms_text?: string | null;
  bank_details?: string | null;
  is_default: boolean;
  created_at: string;
};

export type DashboardKpis = {
  total_invoiced_all_time: number;
  paid_this_month: number;
  overdue_amount: number;
  outstanding_balance: number;
  avg_days_to_payment?: number | null;
  total_invoices: number;
  invoice_counts: {
    draft: number;
    sent: number;
    viewed: number;
    paid: number;
    overdue: number;
    cancelled: number;
  };
};

export type DashboardTrendPoint = {
  month: string;
  invoiced: number;
  paid: number;
  overdue: number;
};

export type DashboardNeedsAttention = {
  overdue: Array<{
    invoice_id: string;
    invoice_number: string;
    buyer_name: string;
    grand_total: number;
    currency: string;
    due_date: string;
    status: string;
    days_overdue?: number | null;
    days_until_due?: number | null;
  }>;
  due_within_7_days: Array<{
    invoice_id: string;
    invoice_number: string;
    buyer_name: string;
    grand_total: number;
    currency: string;
    due_date: string;
    status: string;
    days_overdue?: number | null;
    days_until_due?: number | null;
  }>;
};

export type DashboardTopClients = {
  top_clients: Array<{
    buyer_name: string;
    total_invoiced: number;
    total_paid: number;
    outstanding: number;
    invoice_count: number;
  }>;
};

export type RecurringRule = {
  recurring_id: string;
  owner_id?: string | null;
  name: string;
  frequency: "daily" | "weekly" | "biweekly" | "monthly" | "quarterly" | "annually";
  next_run_date: string;
  end_date?: string | null;
  is_active: boolean;
  last_run_date?: string | null;
  created_at: string;
};

export type AuditLog = {
  audit_id: string;
  entity_type: string;
  entity_id: string;
  action: string;
  changed_by?: string | null;
  changes?: string | null;
  timestamp: string;
};
