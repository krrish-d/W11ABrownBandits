"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import {
  fetchCommunicationLogs,
  fetchInvoice,
  fetchInvoicePaymentSummary,
  getApiError,
  recordPayment,
  sendInvoiceReminder,
  sendInvoiceWithImportLink,
  updateInvoiceStatus,
} from "@/lib/api";
import type { CommunicationLog, Invoice, InvoicePaymentSummary } from "@/lib/types";
import { PageTransition } from "@/components/page-transition";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";

export default function InvoiceDetailPage() {
  const params = useParams<{ id: string }>();
  const id = params?.id;

  const [invoice, setInvoice] = useState<Invoice | null>(null);
  const [logs, setLogs] = useState<CommunicationLog[]>([]);
  const [paymentSummary, setPaymentSummary] = useState<InvoicePaymentSummary | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [recipientEmail, setRecipientEmail] = useState("");
  const [paymentForm, setPaymentForm] = useState({
    amount: "",
    method: "bank_transfer",
    reference: "",
    payment_date: new Date().toISOString().slice(0, 10),
  });
  const [updatingStatus, setUpdatingStatus] = useState(false);
  const [sending, setSending] = useState(false);
  const [recordingPayment, setRecordingPayment] = useState(false);
  const [actionMessage, setActionMessage] = useState("");

  async function refreshData(invoiceId: string) {
    const [invoiceData, allLogs, paymentData] = await Promise.all([
      fetchInvoice(invoiceId, "json") as Promise<Invoice>,
      fetchCommunicationLogs(),
      fetchInvoicePaymentSummary(invoiceId),
    ]);
    setInvoice(invoiceData);
    setRecipientEmail(invoiceData.buyer_email || invoiceData.client_email || "");
    setLogs(allLogs.filter((l) => l.invoice_id === invoiceData.invoice_id));
    setPaymentSummary(paymentData);
  }

  useEffect(() => {
    async function run() {
      if (!id) return;
      try {
        setLoading(true);
        await refreshData(id);
      } catch (e) {
        setError(getApiError(e));
      } finally {
        setLoading(false);
      }
    }

    run();
  }, [id]);

  const status = useMemo(() => (invoice?.status?.toLowerCase() || "draft"), [invoice?.status]);
  const badgeVariant = status === "overdue" ? "overdue" : status === "paid" ? "paid" : "pending";
  const outstanding = paymentSummary?.outstanding_balance ?? invoice?.grand_total ?? 0;

  async function triggerSend() {
    if (!invoice) return;
    try {
      setSending(true);
      setActionMessage("");
      const response = await sendInvoiceWithImportLink(invoice.invoice_id, recipientEmail);
      setActionMessage(`Invoice sent. Import link expires ${new Date(response.token_expires_at).toLocaleString()}.`);
      await refreshData(invoice.invoice_id);
    } catch (e) {
      setActionMessage(getApiError(e));
    } finally {
      setSending(false);
    }
  }

  async function triggerReminder() {
    if (!invoice) return;
    try {
      setSending(true);
      setActionMessage("");
      await sendInvoiceReminder(invoice.invoice_id);
      setActionMessage("Reminder sent successfully.");
      await refreshData(invoice.invoice_id);
    } catch (e) {
      setActionMessage(getApiError(e));
    } finally {
      setSending(false);
    }
  }

  async function handleStatusUpdate(nextStatus: string) {
    if (!invoice) return;
    try {
      setUpdatingStatus(true);
      setActionMessage("");
      await updateInvoiceStatus(invoice.invoice_id, nextStatus);
      await refreshData(invoice.invoice_id);
      setActionMessage(`Status updated to ${nextStatus}.`);
    } catch (e) {
      setActionMessage(getApiError(e));
    } finally {
      setUpdatingStatus(false);
    }
  }

  async function handleRecordPayment() {
    if (!invoice) return;
    const amountNum = Number(paymentForm.amount);
    if (!Number.isFinite(amountNum) || amountNum <= 0) {
      setActionMessage("Enter a valid payment amount.");
      return;
    }
    try {
      setRecordingPayment(true);
      setActionMessage("");
      await recordPayment({
        invoice_id: invoice.invoice_id,
        amount: amountNum,
        method: paymentForm.method,
        reference: paymentForm.reference || undefined,
        payment_date: paymentForm.payment_date,
      });
      setPaymentForm((prev) => ({ ...prev, amount: "", reference: "" }));
      await refreshData(invoice.invoice_id);
      setActionMessage("Payment recorded.");
    } catch (e) {
      setActionMessage(getApiError(e));
    } finally {
      setRecordingPayment(false);
    }
  }

  if (!id) return <p className="muted-text">Missing invoice ID.</p>;
  if (loading) return <div className="h-40 animate-pulse rounded-2xl bg-card" />;
  if (!invoice) return <p className="muted-text">Invoice not found.</p>;

  return (
    <PageTransition>
      <div className="grid gap-6 lg:grid-cols-[1.4fr_1fr]">
        <div className="space-y-6">
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle>{invoice.invoice_number}</CardTitle>
                <Badge variant={badgeVariant}>{status}</Badge>
              </div>
            </CardHeader>
            <CardContent className="grid gap-4 md:grid-cols-2">
              <div>
                <p className="muted-text">Client</p>
                <p className="font-medium">{invoice.buyer_name || invoice.client_name}</p>
                <p className="muted-text">{invoice.buyer_email || invoice.client_email}</p>
              </div>
              <div>
                <p className="muted-text">Due date</p>
                <p className="font-medium">{invoice.due_date}</p>
              </div>
              <div>
                <p className="muted-text">Subtotal</p>
                <p>{invoice.currency} {invoice.subtotal.toFixed(2)}</p>
              </div>
              <div>
                <p className="muted-text">Grand total</p>
                <p className="font-semibold">{invoice.currency} {invoice.grand_total.toFixed(2)}</p>
              </div>
              <div>
                <p className="muted-text">Outstanding</p>
                <p className="font-semibold">{invoice.currency} {outstanding.toFixed(2)}</p>
              </div>
              <div className="md:col-span-2">
                <p className="mb-2 muted-text">Lifecycle status</p>
                <div className="flex flex-wrap gap-2">
                  {["draft", "sent", "viewed", "paid", "overdue", "cancelled"].map((value) => (
                    <Button
                      key={value}
                      type="button"
                      variant={status === value ? "default" : "secondary"}
                      size="sm"
                      disabled={updatingStatus}
                      onClick={() => handleStatusUpdate(value)}
                    >
                      {value}
                    </Button>
                  ))}
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Line items</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                {invoice.items.map((item) => (
                  <div key={item.item_id || item.description} className="grid grid-cols-4 gap-2 rounded-xl border border-border p-3">
                    <p className="col-span-2">{item.description}</p>
                    <p className="muted-text">
                      {item.quantity} x {invoice.currency} {item.unit_price.toFixed(2)}
                    </p>
                    <p className="text-right font-medium">{invoice.currency} {(item.line_total || item.quantity * item.unit_price).toFixed(2)}</p>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Payment tracking</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid gap-3 md:grid-cols-4">
                <Input
                  placeholder="Amount"
                  type="number"
                  step="0.01"
                  value={paymentForm.amount}
                  onChange={(e) => setPaymentForm((s) => ({ ...s, amount: e.target.value }))}
                />
                <select
                  className="h-10 rounded-2xl border border-input bg-background px-3 text-sm"
                  value={paymentForm.method}
                  onChange={(e) => setPaymentForm((s) => ({ ...s, method: e.target.value }))}
                >
                  <option value="bank_transfer">bank_transfer</option>
                  <option value="credit_card">credit_card</option>
                  <option value="cash">cash</option>
                  <option value="xero">xero</option>
                  <option value="other">other</option>
                </select>
                <Input
                  type="date"
                  value={paymentForm.payment_date}
                  onChange={(e) => setPaymentForm((s) => ({ ...s, payment_date: e.target.value }))}
                />
                <Input
                  placeholder="Reference"
                  value={paymentForm.reference}
                  onChange={(e) => setPaymentForm((s) => ({ ...s, reference: e.target.value }))}
                />
              </div>
              <Button onClick={handleRecordPayment} disabled={recordingPayment}>
                {recordingPayment ? "Recording..." : "Record payment"}
              </Button>
              <div className="space-y-2">
                {paymentSummary?.payments.length ? (
                  paymentSummary.payments.map((payment) => (
                    <div key={payment.payment_id} className="flex items-center justify-between rounded-xl border border-border p-3">
                      <div>
                        <p className="font-medium">
                          {invoice.currency} {payment.amount.toFixed(2)} · {payment.method}
                        </p>
                        <p className="muted-text">{payment.reference || "No reference"} · {payment.payment_date}</p>
                      </div>
                    </div>
                  ))
                ) : (
                  <p className="muted-text">No payments recorded yet.</p>
                )}
              </div>
            </CardContent>
          </Card>
        </div>

        <Card>
          <CardHeader>
            <CardTitle>Send & reminders</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <Input
              value={recipientEmail}
              onChange={(e) => setRecipientEmail(e.target.value)}
              placeholder="Recipient email"
            />
            <div className="flex gap-2">
              <Button onClick={() => triggerSend()} disabled={sending}>
                Send Invoice Email
              </Button>
              <Button variant="secondary" onClick={() => triggerReminder()} disabled={sending}>
                Send Reminder
              </Button>
            </div>
            {actionMessage ? <p className="muted-text">{actionMessage}</p> : null}

            <div className="rounded-xl border border-border p-3">
              <p className="mb-2 text-sm font-medium">Communication log</p>
              {logs.length === 0 ? (
                <p className="muted-text">No logs yet.</p>
              ) : (
                <ul className="space-y-2">
                  {logs.map((log, idx) => (
                    <li key={`${log.log_id || log.sent_at || log.timestamp}-${idx}`} className="text-sm">
                      <span className="font-medium">{log.recipient_email}</span> -{" "}
                      <span className="text-muted-foreground">
                        {new Date(log.sent_at || log.timestamp || Date.now()).toLocaleString()}
                      </span>{" "}
                      <span className="muted-text">({log.delivery_status || "sent"})</span>
                    </li>
                  ))}
                </ul>
              )}
            </div>

            <Link href={`/compose?id=${invoice.invoice_id}`}>
              <Button variant="ghost">Edit invoice</Button>
            </Link>
            {error ? <p className="muted-text text-rose-700">{error}</p> : null}
          </CardContent>
        </Card>
      </div>
    </PageTransition>
  );
}
