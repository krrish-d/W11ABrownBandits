"use client";

import { useEffect, useMemo, useState } from "react";
import { createClient, fetchClients, getApiError } from "@/lib/api";
import type { Client } from "@/lib/types";
import { PageTransition } from "@/components/page-transition";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";

export default function ClientsPage() {
  const [clients, setClients] = useState<Client[]>([]);
  const [search, setSearch] = useState("");
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(true);
  const [form, setForm] = useState({
    name: "",
    email: "",
    address: "",
    tax_id: "",
    currency: "AUD",
    payment_terms: "30",
    notes: "",
  });

  async function loadClients() {
    try {
      setLoading(true);
      const data = await fetchClients(search || undefined);
      setClients(data);
    } catch (error) {
      setMessage(getApiError(error));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadClients();
  }, [search]);

  const summary = useMemo(
    () => ({
      total: clients.length,
      withTaxId: clients.filter((c) => !!c.tax_id).length,
    }),
    [clients]
  );

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    try {
      setMessage("");
      await createClient({
        name: form.name,
        email: form.email,
        address: form.address || undefined,
        tax_id: form.tax_id || undefined,
        currency: form.currency,
        payment_terms: Number(form.payment_terms),
        notes: form.notes || undefined,
      });
      setForm({
        name: "",
        email: "",
        address: "",
        tax_id: "",
        currency: "AUD",
        payment_terms: "30",
        notes: "",
      });
      setMessage("Client created.");
      await loadClients();
    } catch (error) {
      setMessage(getApiError(error));
    }
  }

  return (
    <PageTransition>
      <div className="space-y-6">
        <div>
          <h2 className="text-2xl font-semibold">Clients</h2>
          <p className="muted-text">Reusable client profiles with payment terms and tax metadata.</p>
        </div>

        <div className="grid gap-4 md:grid-cols-2">
          <Card>
            <CardContent className="p-5">
              <p className="text-sm text-muted-foreground">Total clients</p>
              <p className="mt-1 text-2xl font-semibold">{summary.total}</p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-5">
              <p className="text-sm text-muted-foreground">With tax ID</p>
              <p className="mt-1 text-2xl font-semibold">{summary.withTaxId}</p>
            </CardContent>
          </Card>
        </div>

        <Card>
          <CardHeader>
            <CardTitle>Add client</CardTitle>
          </CardHeader>
          <CardContent>
            <form className="space-y-3" onSubmit={onSubmit}>
              <div className="grid gap-3 md:grid-cols-2">
                <Input placeholder="Name" value={form.name} onChange={(e) => setForm((s) => ({ ...s, name: e.target.value }))} />
                <Input placeholder="Email" value={form.email} onChange={(e) => setForm((s) => ({ ...s, email: e.target.value }))} />
                <Input placeholder="Address" value={form.address} onChange={(e) => setForm((s) => ({ ...s, address: e.target.value }))} />
                <Input placeholder="Tax ID (ABN/VAT)" value={form.tax_id} onChange={(e) => setForm((s) => ({ ...s, tax_id: e.target.value }))} />
                <select
                  className="h-10 rounded-2xl border border-input bg-background px-3 text-sm"
                  value={form.currency}
                  onChange={(e) => setForm((s) => ({ ...s, currency: e.target.value }))}
                >
                  <option value="AUD">AUD</option>
                  <option value="USD">USD</option>
                  <option value="GBP">GBP</option>
                  <option value="EUR">EUR</option>
                </select>
                <Input
                  type="number"
                  min={1}
                  placeholder="Payment terms (days)"
                  value={form.payment_terms}
                  onChange={(e) => setForm((s) => ({ ...s, payment_terms: e.target.value }))}
                />
              </div>
              <Textarea
                rows={3}
                placeholder="Internal notes"
                value={form.notes}
                onChange={(e) => setForm((s) => ({ ...s, notes: e.target.value }))}
              />
              <Button type="submit">Save client</Button>
            </form>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Client library</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <Input placeholder="Search by name or email" value={search} onChange={(e) => setSearch(e.target.value)} />
            {loading ? (
              <p className="muted-text">Loading clients...</p>
            ) : clients.length === 0 ? (
              <p className="muted-text">No clients yet.</p>
            ) : (
              clients.map((client) => (
                <div key={client.client_id} className="rounded-xl border border-border p-3">
                  <p className="font-medium">{client.name}</p>
                  <p className="muted-text">{client.email}</p>
                  <p className="muted-text">{client.address || "No address"}</p>
                </div>
              ))
            )}
            {message ? <p className="muted-text">{message}</p> : null}
          </CardContent>
        </Card>
      </div>
    </PageTransition>
  );
}
