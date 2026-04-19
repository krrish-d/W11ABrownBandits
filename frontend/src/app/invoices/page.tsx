"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { Search, Trash2, Upload } from "lucide-react";
import { fetchInvoices, getApiError, parseInvoiceFile, removeInvoice, sendInvoiceWithImportLink } from "@/lib/api";
import type { Invoice } from "@/lib/types";
import { PageTransition } from "@/components/page-transition";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

type SendState = { invoiceId: string; email: string; loading: boolean; done: string };

type FilterStatus = "all" | "draft" | "sent" | "viewed" | "paid" | "overdue" | "cancelled";

export default function InvoicesPage() {
  const router = useRouter();
  const [invoices, setInvoices] = useState<Invoice[]>([]);
  const [query, setQuery] = useState("");
  const [status, setStatus] = useState<FilterStatus>("all");
  const [sortBy, setSortBy] = useState("created_at");
  const [sortOrder, setSortOrder] = useState<"asc" | "desc">("desc");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [sendState, setSendState] = useState<SendState | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [confirmDeleteId, setConfirmDeleteId] = useState<string | null>(null);
  const [importLoading, setImportLoading] = useState(false);
  const importFileRef = useRef<HTMLInputElement>(null);

  async function handleImportFile(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    e.target.value = "";
    try {
      setImportLoading(true);
      const parsed = await parseInvoiceFile(file);
      sessionStorage.setItem("invoice_import_data", JSON.stringify(parsed));
      router.push("/compose");
    } catch (err) {
      setError(getApiError(err));
    } finally {
      setImportLoading(false);
    }
  }

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

  async function handleDelete(invoiceId: string) {
    try {
      setDeletingId(invoiceId);
      await removeInvoice(invoiceId);
      setInvoices((prev) => prev.filter((inv) => inv.invoice_id !== invoiceId));
    } catch (e) {
      setError(getApiError(e));
    } finally {
      setDeletingId(null);
      setConfirmDeleteId(null);
    }
  }

  return (
    <PageTransition>
      <div className="space-y-6">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h2 className="text-2xl font-semibold">Invoices</h2>
            <p className="muted-text">Search, filter and inspect all invoice records.</p>
          </div>
          <div className="flex gap-2">
            <input
              ref={importFileRef}
              type="file"
              accept=".json,.csv,.xml,.pdf"
              className="hidden"
              onChange={handleImportFile}
            />
            <Button
              type="button"
              variant="secondary"
              disabled={importLoading}
              onClick={() => importFileRef.current?.click()}
            >
              <Upload className="mr-2 h-4 w-4" />
              {importLoading ? "Parsing…" : "Import from file"}
            </Button>
            <Link href="/compose">
              <Button type="button">New invoice</Button>
            </Link>
          </div>
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
                  const isSending = sendState?.invoiceId === invoice.invoice_id;
                  return (
                    <div key={invoice.invoice_id} className="rounded-2xl border border-border p-4 space-y-3">
                      <div className="grid gap-3 md:grid-cols-[1.2fr_1fr_1fr_0.8fr_auto]">
                        <div>
                          <Link href={`/invoices/${invoice.invoice_id}`} className="font-medium underline-offset-2 hover:underline">
                            {invoice.invoice_number}
                          </Link>
                          <p className="muted-text">{invoice.buyer_name || invoice.client_name}</p>
                        </div>
                        <div className="muted-text">{invoice.buyer_email || invoice.client_email}</div>
                        <div className="muted-text">
                          {invoice.currency} {invoice.grand_total.toFixed(2)}
                        </div>
                        <div className="justify-self-start md:justify-self-end">
                          <Badge variant={badgeVariant}>{computedStatus}</Badge>
                        </div>
                        <div className="flex flex-wrap gap-2 justify-self-start md:justify-self-end">
                          <Link href={`/transform?invoiceId=${invoice.invoice_id}`}>
                            <Button type="button" variant="secondary" size="sm">Transform</Button>
                          </Link>
                          <Link href={`/validate?invoiceId=${invoice.invoice_id}`}>
                            <Button type="button" variant="secondary" size="sm">Validate</Button>
                          </Link>
                          <Button
                            type="button"
                            variant="secondary"
                            size="sm"
                            onClick={() =>
                              setSendState(isSending ? null : { invoiceId: invoice.invoice_id, email: invoice.buyer_email || invoice.client_email, loading: false, done: "" })
                            }
                          >
                            Send
                          </Button>
                          {confirmDeleteId === invoice.invoice_id ? (
                            <>
                              <Button
                                type="button"
                                variant="destructive"
                                size="sm"
                                disabled={deletingId === invoice.invoice_id}
                                onClick={() => handleDelete(invoice.invoice_id)}
                              >
                                {deletingId === invoice.invoice_id ? "Deleting…" : "Confirm delete"}
                              </Button>
                              <Button
                                type="button"
                                variant="ghost"
                                size="sm"
                                onClick={() => setConfirmDeleteId(null)}
                              >
                                Cancel
                              </Button>
                            </>
                          ) : (
                            <Button
                              type="button"
                              variant="ghost"
                              size="sm"
                              className="text-rose-500 hover:bg-rose-50 hover:text-rose-700"
                              onClick={() => setConfirmDeleteId(invoice.invoice_id)}
                            >
                              <Trash2 className="h-4 w-4" />
                            </Button>
                          )}
                        </div>
                      </div>

                      {/* Inline send email row */}
                      {isSending ? (
                        <div className="flex flex-wrap gap-2">
                          <Input
                            type="email"
                            className="max-w-xs"
                            placeholder="Recipient email"
                            value={sendState!.email}
                            onChange={(e) => setSendState((s) => s ? { ...s, email: e.target.value } : null)}
                          />
                          <Button
                            type="button"
                            size="sm"
                            disabled={sendState!.loading || !sendState!.email}
                            onClick={async () => {
                              setSendState((s) => s ? { ...s, loading: true, done: "" } : null);
                              try {
                                await sendInvoiceWithImportLink(invoice.invoice_id, sendState!.email);
                                setSendState((s) => s ? { ...s, loading: false, done: `Sent to ${s.email}` } : null);
                              } catch (e) {
                                setSendState((s) => s ? { ...s, loading: false, done: getApiError(e) } : null);
                              }
                            }}
                          >
                            {sendState!.loading ? "Sending…" : "Send email"}
                          </Button>
                          <Button type="button" variant="ghost" size="sm" onClick={() => setSendState(null)}>
                            Cancel
                          </Button>
                          {sendState!.done ? <p className="self-center text-sm text-muted-foreground">{sendState!.done}</p> : null}
                        </div>
                      ) : null}
                    </div>
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
