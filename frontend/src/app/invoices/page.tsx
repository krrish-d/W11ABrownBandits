"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { Search } from "lucide-react";
import { fetchInvoices, getApiError } from "@/lib/api";
import type { Invoice } from "@/lib/types";
import { PageTransition } from "@/components/page-transition";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";

type FilterStatus = "all" | "draft" | "sent" | "viewed" | "paid" | "overdue" | "cancelled";

export default function InvoicesPage() {
  const [invoices, setInvoices] = useState<Invoice[]>([]);
  const [query, setQuery] = useState("");
  const [status, setStatus] = useState<FilterStatus>("all");
  const [sortBy, setSortBy] = useState("created_at");
  const [sortOrder, setSortOrder] = useState<"asc" | "desc">("desc");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    setLoading(true);
    fetchInvoices({
      search: query || undefined,
      status: status === "all" ? undefined : status,
      sort_by: sortBy,
      sort_order: sortOrder,
      page_size: 100,
    })
      .then(setInvoices)
      .catch((e) => setError(getApiError(e)))
      .finally(() => setLoading(false));
  }, [query, status, sortBy, sortOrder]);

  return (
    <PageTransition>
      <div className="space-y-6">
        <div>
          <h2 className="text-2xl font-semibold">Invoices</h2>
          <p className="muted-text">Search, filter and inspect all invoice records.</p>
        </div>

        <Card>
          <CardContent className="flex flex-col gap-3 p-4 md:flex-row">
            <div className="relative flex-1">
              <Search className="pointer-events-none absolute left-3 top-3.5 h-4 w-4 text-muted-foreground" />
              <Input className="pl-9" placeholder="Search by number, client, or email" value={query} onChange={(e) => setQuery(e.target.value)} />
            </div>
            <select
              className="h-10 rounded-2xl border border-input bg-background px-3 text-sm"
              value={status}
              onChange={(e) => setStatus(e.target.value as FilterStatus)}
            >
              <option value="all">All statuses</option>
              <option value="draft">Draft</option>
              <option value="sent">Sent</option>
              <option value="viewed">Viewed</option>
              <option value="paid">Paid</option>
              <option value="overdue">Overdue</option>
              <option value="cancelled">Cancelled</option>
            </select>
            <select
              className="h-10 rounded-2xl border border-input bg-background px-3 text-sm"
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value)}
            >
              <option value="created_at">Newest</option>
              <option value="due_date">Due date</option>
              <option value="grand_total">Amount</option>
              <option value="buyer_name">Client</option>
            </select>
            <select
              className="h-10 rounded-2xl border border-input bg-background px-3 text-sm"
              value={sortOrder}
              onChange={(e) => setSortOrder(e.target.value as "asc" | "desc")}
            >
              <option value="desc">Desc</option>
              <option value="asc">Asc</option>
            </select>
          </CardContent>
        </Card>

        {error ? <p className="muted-text text-rose-700">{error}</p> : null}

        <Card>
          <CardHeader>
            <CardTitle>Invoice list</CardTitle>
          </CardHeader>
          <CardContent>
            {loading ? (
              <p className="muted-text">Loading invoices...</p>
            ) : invoices.length === 0 ? (
              <p className="muted-text">No invoices match the current filters.</p>
            ) : (
              <div className="space-y-2">
                {invoices.map((invoice) => {
                  const computedStatus = (invoice.status?.toLowerCase() || "draft") as
                    | "draft"
                    | "sent"
                    | "viewed"
                    | "paid"
                    | "overdue"
                    | "cancelled";
                  const badgeVariant = computedStatus === "overdue" ? "overdue" : computedStatus === "paid" ? "paid" : "pending";
                  return (
                    <Link
                      href={`/invoices/${invoice.invoice_id}`}
                      key={invoice.invoice_id}
                      className="grid gap-3 rounded-2xl border border-border p-4 transition hover:bg-cream md:grid-cols-[1.2fr_1fr_1fr_0.8fr]"
                    >
                      <div>
                        <p className="font-medium">{invoice.invoice_number}</p>
                        <p className="muted-text">{invoice.buyer_name || invoice.client_name}</p>
                      </div>
                      <div className="muted-text">{invoice.buyer_email || invoice.client_email}</div>
                      <div className="muted-text">
                        {invoice.currency} {invoice.grand_total.toFixed(2)}
                      </div>
                      <div className="justify-self-start md:justify-self-end">
                        <Badge variant={badgeVariant}>{computedStatus}</Badge>
                      </div>
                    </Link>
                  );
                })}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </PageTransition>
  );
}
