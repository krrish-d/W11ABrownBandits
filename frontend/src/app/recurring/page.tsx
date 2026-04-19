"use client";

import { useEffect, useState } from "react";
import { createRecurringRule, deleteRecurringRule, fetchRecurringRules, getApiError } from "@/lib/api";
import type { RecurringRule } from "@/lib/types";
import { PageTransition } from "@/components/page-transition";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";

type DraftLineItem = {
  description: string;
  quantity: number;
  unit_price: number;
  tax_rate: number;
};

const DEFAULT_ITEM: DraftLineItem = { description: "", quantity: 1, unit_price: 0, tax_rate: 10 };

export default function RecurringPage() {
  const [rules, setRules] = useState<RecurringRule[]>([]);
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(true);
  const [form, setForm] = useState({
    name: "Monthly consulting invoice",
    frequency: "monthly",
    next_run_date: "",
    end_date: "",
    seller_name: "",
    seller_address: "",
    seller_email: "",
    buyer_name: "",
    buyer_address: "",
    buyer_email: "",
    currency: "AUD",
    due_date: "",
    notes: "",
    items: [{ ...DEFAULT_ITEM }],
  });

  async function loadRules() {
    try {
      setLoading(true);
      const data = await fetchRecurringRules();
      setRules(data);
    } catch (error) {
      setMessage(getApiError(error));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadRules();
  }, []);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    try {
      setMessage("");
      await createRecurringRule({
        name: form.name,
        frequency: form.frequency,
        next_run_date: form.next_run_date,
        end_date: form.end_date || undefined,
        invoice_template: {
          seller_name: form.seller_name,
          seller_address: form.seller_address,
          seller_email: form.seller_email,
          buyer_name: form.buyer_name,
          buyer_address: form.buyer_address,
          buyer_email: form.buyer_email,
          currency: form.currency,
          due_date: form.due_date,
          notes: form.notes || undefined,
          items: form.items.map((item, index) => ({
            item_number: String(index + 1),
            description: item.description,
            quantity: Number(item.quantity),
            unit_price: Number(item.unit_price),
            tax_rate: Number(item.tax_rate),
          })),
        },
      });
      setMessage("Recurring rule created.");
      setForm((prev) => ({
        ...prev,
        name: "Monthly consulting invoice",
        end_date: "",
        notes: "",
        items: [{ ...DEFAULT_ITEM }],
      }));
      await loadRules();
    } catch (error) {
      setMessage(getApiError(error));
    }
  }

  async function onDelete(recurringId: string) {
    try {
      setMessage("");
      await deleteRecurringRule(recurringId);
      setMessage("Recurring rule deleted.");
      await loadRules();
    } catch (error) {
      setMessage(getApiError(error));
    }
  }

  function updateItem(index: number, patch: Partial<DraftLineItem>) {
    setForm((prev) => ({
      ...prev,
      items: prev.items.map((item, i) => (i === index ? { ...item, ...patch } : item)),
    }));
  }

  function addItem() {
    setForm((prev) => ({ ...prev, items: [...prev.items, { ...DEFAULT_ITEM }] }));
  }

  function removeItem(index: number) {
    setForm((prev) => ({
      ...prev,
      items: prev.items.length === 1 ? prev.items : prev.items.filter((_, i) => i !== index),
    }));
  }

  return (
    <PageTransition>
      <div className="space-y-6">
        <div>
          <h2 className="text-2xl font-semibold">Recurring</h2>
          <p className="muted-text">Set invoice templates to auto-generate on a schedule.</p>
        </div>

        <Card>
          <CardHeader>
            <CardTitle>Create recurring rule</CardTitle>
          </CardHeader>
          <CardContent>
            <form className="space-y-3" onSubmit={onSubmit}>
              <div className="grid gap-3 md:grid-cols-4">
                <Input placeholder="Rule name" value={form.name} onChange={(e) => setForm((s) => ({ ...s, name: e.target.value }))} />
                <select
                  className="h-10 rounded-2xl border border-input bg-background px-3 text-sm"
                  value={form.frequency}
                  onChange={(e) => setForm((s) => ({ ...s, frequency: e.target.value }))}
                >
                  <option value="daily">daily</option>
                  <option value="weekly">weekly</option>
                  <option value="biweekly">biweekly</option>
                  <option value="monthly">monthly</option>
                  <option value="quarterly">quarterly</option>
                  <option value="annually">annually</option>
                </select>
                <Input
                  type="date"
                  value={form.next_run_date}
                  onChange={(e) => setForm((s) => ({ ...s, next_run_date: e.target.value }))}
                />
                <Input
                  type="date"
                  value={form.end_date}
                  onChange={(e) => setForm((s) => ({ ...s, end_date: e.target.value }))}
                />
              </div>
              <div className="grid gap-3 md:grid-cols-2">
                <Input placeholder="Seller name" value={form.seller_name} onChange={(e) => setForm((s) => ({ ...s, seller_name: e.target.value }))} />
                <Input placeholder="Seller email" value={form.seller_email} onChange={(e) => setForm((s) => ({ ...s, seller_email: e.target.value }))} />
                <Input
                  className="md:col-span-2"
                  placeholder="Seller address"
                  value={form.seller_address}
                  onChange={(e) => setForm((s) => ({ ...s, seller_address: e.target.value }))}
                />
                <Input placeholder="Buyer name" value={form.buyer_name} onChange={(e) => setForm((s) => ({ ...s, buyer_name: e.target.value }))} />
                <Input placeholder="Buyer email" value={form.buyer_email} onChange={(e) => setForm((s) => ({ ...s, buyer_email: e.target.value }))} />
                <Input
                  className="md:col-span-2"
                  placeholder="Buyer address"
                  value={form.buyer_address}
                  onChange={(e) => setForm((s) => ({ ...s, buyer_address: e.target.value }))}
                />
                <Input type="date" value={form.due_date} onChange={(e) => setForm((s) => ({ ...s, due_date: e.target.value }))} />
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
              </div>
              <div>
                <label className="muted-text">Notes</label>
                <Textarea rows={3} value={form.notes} onChange={(e) => setForm((s) => ({ ...s, notes: e.target.value }))} />
              </div>
              <div className="space-y-2">
                <div className="hidden gap-2 px-1 text-xs font-medium text-muted-foreground md:grid md:grid-cols-6">
                  <p>Description</p>
                  <p>Quantity</p>
                  <p>Unit Price</p>
                  <p>Tax %</p>
                  <p>Total</p>
                  <p>Action</p>
                </div>
                {form.items.map((item, index) => {
                  const lineTotal = Number(item.quantity || 0) * Number(item.unit_price || 0) * (1 + Number(item.tax_rate || 0) / 100);
                  return (
                    <div key={`${index}-${item.description}`} className="grid gap-2 rounded-xl border border-border p-3 md:grid-cols-6">
                      <Input value={item.description} onChange={(e) => updateItem(index, { description: e.target.value })} placeholder="Description" />
                      <Input
                        type="number"
                        step="1"
                        value={item.quantity}
                        onChange={(e) => updateItem(index, { quantity: Number(e.target.value) || 0 })}
                      />
                      <Input
                        type="number"
                        step="0.01"
                        value={item.unit_price}
                        onChange={(e) => updateItem(index, { unit_price: Number(e.target.value) || 0 })}
                      />
                      <Input
                        type="number"
                        step="0.1"
                        value={item.tax_rate}
                        onChange={(e) => updateItem(index, { tax_rate: Number(e.target.value) || 0 })}
                      />
                      <div className="flex items-center rounded-2xl border border-input bg-background px-3 text-sm">
                        {form.currency} {lineTotal.toFixed(2)}
                      </div>
                      <div className="flex items-center">
                        <Button type="button" variant="ghost" onClick={() => removeItem(index)} disabled={form.items.length === 1}>
                          Remove
                        </Button>
                      </div>
                    </div>
                  );
                })}
                <Button type="button" variant="secondary" onClick={addItem}>
                  Add line item
                </Button>
              </div>
              <div className="flex gap-2">
                <Button type="submit">Save recurring rule</Button>
              </div>
            </form>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Recurring rules</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {loading ? (
              <p className="muted-text">Loading recurring rules...</p>
            ) : rules.length === 0 ? (
              <p className="muted-text">No recurring rules yet.</p>
            ) : (
              rules.map((rule) => (
                <div key={rule.recurring_id} className="rounded-xl border border-border p-3">
                  <div className="flex items-center justify-between gap-3">
                    <div>
                      <p className="font-medium">{rule.name}</p>
                      <p className="muted-text">
                        Next run: {rule.next_run_date} - Frequency: {rule.frequency}
                      </p>
                      <p className="text-xs text-muted-foreground">{rule.is_active ? "Active" : "Paused"}</p>
                    </div>
                    <Button type="button" variant="secondary" onClick={() => onDelete(rule.recurring_id)}>
                      Delete
                    </Button>
                  </div>
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
