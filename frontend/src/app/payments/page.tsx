"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { fetchInvoices, fetchInvoicePaymentSummary, getApiError } from "@/lib/api";
import type { Invoice, InvoicePaymentSummary } from "@/lib/types";
import { PageTransition } from "@/components/page-transition";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export default function PaymentsPage() {
  const [invoices, setInvoices] = useState<Invoice[]>([]);
  const [selectedInvoiceId, setSelectedInvoiceId] = useState("");
  const [summary, setSummary] = useState<InvoicePaymentSummary | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    fetchInvoices({ page_size: 100 })
      .then((data) => {
        setInvoices(data);
        if (data[0]) setSelectedInvoiceId(data[0].invoice_id);
      })
      .catch((e) => setError(getApiError(e)));
  }, []);

  useEffect(() => {
    if (!selectedInvoiceId) return;
    fetchInvoicePaymentSummary(selectedInvoiceId)
      .then(setSummary)
      .catch((e) => setError(getApiError(e)));
  }, [selectedInvoiceId]);

  return (
    <PageTransition>
      <div className="space-y-6">
        <div>
          <h2 className="text-2xl font-semibold">Payments</h2>
          <p className="muted-text">Track paid amounts and outstanding balances by invoice.</p>
        </div>
        {error ? <p className="muted-text text-rose-700">{error}</p> : null}

        <Card>
          <CardHeader>
            <CardTitle>Invoice payment summary</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <select
              className="h-10 w-full rounded-2xl border border-input bg-background px-3 text-sm"
              value={selectedInvoiceId}
              onChange={(e) => setSelectedInvoiceId(e.target.value)}
            >
              {invoices.map((invoice) => (
                <option key={invoice.invoice_id} value={invoice.invoice_id}>
                  {invoice.invoice_number} - {invoice.buyer_name || invoice.client_name}
                </option>
              ))}
            </select>

            {!summary ? (
              <p className="muted-text">No summary available yet.</p>
            ) : (
              <div className="space-y-2">
                <div className="grid grid-cols-3 gap-2 rounded-xl border border-border p-3 text-sm">
                  <p>Total: {summary.grand_total.toFixed(2)}</p>
                  <p>Paid: {summary.total_paid.toFixed(2)}</p>
                  <p>Outstanding: {summary.outstanding_balance.toFixed(2)}</p>
                </div>
                {summary.payments.length ? (
                  summary.payments.map((payment) => (
                    <div key={payment.payment_id} className="rounded-xl border border-border p-3 text-sm">
                      <p className="font-medium">
                        {payment.amount.toFixed(2)} via {payment.method}
                      </p>
                      <p className="muted-text">
                        {payment.payment_date} · {payment.reference || "No reference"}
                      </p>
                    </div>
                  ))
                ) : (
                  <p className="muted-text">No payments recorded for this invoice.</p>
                )}
                <Link href={`/invoices/${summary.invoice_id}`} className="inline-block text-sm underline">
                  Open invoice to record a payment
                </Link>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </PageTransition>
  );
}
