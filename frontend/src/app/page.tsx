"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { ArrowRight, ShieldCheck, Wand2 } from "lucide-react";
import {
  fetchDashboardKpis,
  fetchDashboardNeedsAttention,
  fetchInvoices,
  fetchMe,
  getApiError,
} from "@/lib/api";
import type { DashboardKpis, DashboardNeedsAttention, Invoice, User } from "@/lib/types";
import { PageTransition } from "@/components/page-transition";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";

export default function DashboardPage() {
  const [invoices, setInvoices] = useState<Invoice[]>([]);
  const [kpis, setKpis] = useState<DashboardKpis | null>(null);
  const [attention, setAttention] = useState<DashboardNeedsAttention | null>(null);
  const [user, setUser] = useState<User | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.allSettled([fetchInvoices({ page_size: 8 }), fetchDashboardKpis(), fetchDashboardNeedsAttention(), fetchMe()])
      .then((results) => {
        const [invoiceRes, kpiRes, attentionRes, userRes] = results;
        if (invoiceRes.status === "fulfilled") setInvoices(invoiceRes.value);
        if (kpiRes.status === "fulfilled") setKpis(kpiRes.value);
        if (attentionRes.status === "fulfilled") setAttention(attentionRes.value);
        if (userRes.status === "fulfilled") setUser(userRes.value);
      })
      .catch((e) => setError(getApiError(e)))
      .finally(() => setLoading(false));
  }, []);

  const stats = useMemo(() => {
    const statuses = invoices.map((i) => i.status?.toLowerCase() || "draft");
    return {
      total: invoices.length,
      pending: statuses.filter((s) => ["draft", "sent", "viewed"].includes(s)).length,
      paid: statuses.filter((s) => s === "paid").length,
      overdue: statuses.filter((s) => s === "overdue").length,
    };
  }, [invoices]);

  return (
    <PageTransition>
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-2xl font-semibold">Dashboard</h2>
            <p className="muted-text">
              {user ? `Welcome back, ${user.full_name || user.email}.` : "A calm overview of your invoicing activity."}
            </p>
          </div>
          <Link href="/compose">
            <Button>
              New Invoice <ArrowRight className="ml-2 h-4 w-4" />
            </Button>
          </Link>
        </div>

        {error ? <p className="muted-text text-rose-700">{error}</p> : null}

        <div className="grid gap-4 md:grid-cols-4">
          {[
            ["Total", kpis?.total_invoices ?? stats.total],
            ["Pending", (kpis?.invoice_counts.draft || 0) + (kpis?.invoice_counts.sent || 0) + (kpis?.invoice_counts.viewed || 0) || stats.pending],
            ["Paid", kpis?.invoice_counts.paid ?? stats.paid],
            ["Overdue", kpis?.invoice_counts.overdue ?? stats.overdue],
          ].map(([label, value]) => (
            <Card key={String(label)}>
              <CardContent className="p-5">
                <p className="text-sm text-muted-foreground">{label}</p>
                <p className="mt-1 text-2xl font-semibold">{value}</p>
              </CardContent>
            </Card>
          ))}
        </div>

        <div className="grid gap-4 md:grid-cols-3">
          <Card>
            <CardContent className="p-5">
              <p className="text-sm text-muted-foreground">Total invoiced</p>
              <p className="mt-1 text-xl font-semibold">${(kpis?.total_invoiced_all_time || 0).toFixed(2)}</p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-5">
              <p className="text-sm text-muted-foreground">Paid this month</p>
              <p className="mt-1 text-xl font-semibold">${(kpis?.paid_this_month || 0).toFixed(2)}</p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-5">
              <p className="text-sm text-muted-foreground">Outstanding balance</p>
              <p className="mt-1 text-xl font-semibold">${(kpis?.outstanding_balance || 0).toFixed(2)}</p>
            </CardContent>
          </Card>
        </div>

        <Card>
          <CardHeader>
            <CardTitle>Validation & transformation</CardTitle>
            <CardDescription>Quick access to format conversion and XML rule checks.</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid gap-3 md:grid-cols-2">
              <Link href="/transform" className="rounded-xl border border-border p-4 transition hover:bg-cream">
                <p className="flex items-center gap-2 font-medium">
                  <Wand2 className="h-4 w-4" />
                  Transform invoice formats
                </p>
                <p className="mt-1 text-sm text-muted-foreground">Convert JSON, XML, UBL, CSV and PDF.</p>
              </Link>
              <Link href="/validate" className="rounded-xl border border-border p-4 transition hover:bg-cream">
                <p className="flex items-center gap-2 font-medium">
                  <ShieldCheck className="h-4 w-4" />
                  Validate XML rules
                </p>
                <p className="mt-1 text-sm text-muted-foreground">Run UBL, PEPPOL and Australian checks.</p>
              </Link>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Needs attention</CardTitle>
            <CardDescription>Overdue and due-soon invoices surfaced by backend analytics.</CardDescription>
          </CardHeader>
          <CardContent>
            {!attention || (attention.overdue.length === 0 && attention.due_within_7_days.length === 0) ? (
              <p className="muted-text">No urgent invoices right now.</p>
            ) : (
              <div className="space-y-2">
                {attention.overdue.slice(0, 4).map((item) => (
                  <Link
                    key={item.invoice_id}
                    href={`/invoices/${item.invoice_id}`}
                    className="flex items-center justify-between rounded-xl border border-border p-3 transition hover:bg-cream"
                  >
                    <div>
                      <p className="font-medium">{item.invoice_number}</p>
                      <p className="muted-text">{item.buyer_name}</p>
                    </div>
                    <Badge variant="overdue">{item.days_overdue}d overdue</Badge>
                  </Link>
                ))}
                {attention.due_within_7_days.slice(0, 3).map((item) => (
                  <Link
                    key={item.invoice_id}
                    href={`/invoices/${item.invoice_id}`}
                    className="flex items-center justify-between rounded-xl border border-border p-3 transition hover:bg-cream"
                  >
                    <div>
                      <p className="font-medium">{item.invoice_number}</p>
                      <p className="muted-text">{item.buyer_name}</p>
                    </div>
                    <Badge variant="pending">due in {item.days_until_due}d</Badge>
                  </Link>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Recent invoices</CardTitle>
            <CardDescription>Latest five from your backend</CardDescription>
          </CardHeader>
          <CardContent>
            {loading ? (
              <div className="space-y-3">
                {[1, 2, 3].map((i) => (
                  <div key={i} className="h-12 rounded-xl bg-muted" />
                ))}
              </div>
            ) : invoices.length === 0 ? (
              <p className="muted-text">No invoices yet. Create your first invoice.</p>
            ) : (
              <div className="space-y-2">
                {invoices.slice(0, 5).map((invoice) => (
                  <Link
                    key={invoice.invoice_id}
                    href={`/invoices/${invoice.invoice_id}`}
                    className="flex items-center justify-between rounded-xl border border-border p-3 transition hover:bg-cream"
                  >
                    <span className="font-medium">{invoice.invoice_number}</span>
                    <span className="muted-text">{invoice.client_name}</span>
                  </Link>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </PageTransition>
  );
}
