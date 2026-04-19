"use client";

import { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";
import { useFieldArray, useForm } from "react-hook-form";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import {
  createInvoice,
  createClient,
  fetchClients,
  fetchInvoice,
  fetchTemplates,
  getApiError,
  updateInvoice,
} from "@/lib/api";
import type { Client, Invoice, Template } from "@/lib/types";
import { PageTransition } from "@/components/page-transition";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";

const lineItemSchema = z.object({
  description: z.string().min(1, "Description is required"),
  quantity: z.coerce.number().min(1),
  unit_price: z.coerce.number().min(0),
  tax_rate: z.coerce.number().min(0).max(100),
});

const schema = z.object({
  seller_name: z.string().min(2),
  seller_address: z.string().min(4),
  seller_email: z.string().email(),
  buyer_name: z.string().min(2),
  buyer_address: z.string().min(4),
  buyer_email: z.string().email(),
  currency: z.enum(["AUD", "USD", "GBP", "EUR"]),
  due_date: z.string().min(1),
  notes: z.string().optional(),
  items: z.array(lineItemSchema).min(1),
});

type FormValues = z.infer<typeof schema>;

export default function ComposePage() {
  const params = useSearchParams();
  const editId = params?.get("id");
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);
  const [clients, setClients] = useState<Client[]>([]);
  const [templates, setTemplates] = useState<Template[]>([]);
  const [selectedClientId, setSelectedClientId] = useState("");
  const [selectedTemplateId, setSelectedTemplateId] = useState("");

  const form = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: {
      seller_name: "",
      seller_address: "",
      seller_email: "",
      buyer_name: "",
      buyer_address: "",
      buyer_email: "",
      currency: "AUD",
      due_date: "",
      notes: "",
      items: [{ description: "", quantity: 1, unit_price: 0, tax_rate: 10 }],
    },
  });

  const { fields, append, remove } = useFieldArray({ control: form.control, name: "items" });

  useEffect(() => {
    Promise.allSettled([fetchClients(), fetchTemplates()]).then((results) => {
      const [clientRes, templateRes] = results;
      if (clientRes.status === "fulfilled") setClients(clientRes.value);
      if (templateRes.status === "fulfilled") setTemplates(templateRes.value);
    });
  }, []);

  useEffect(() => {
    if (!editId) return;
    fetchInvoice(editId, "json")
      .then((data) => {
        const invoice = data as Invoice;
        form.reset({
          seller_name: invoice.seller_name || "",
          seller_address: invoice.seller_address || "",
          seller_email: invoice.seller_email || "",
          buyer_name: invoice.buyer_name || invoice.client_name,
          buyer_address: invoice.buyer_address || "",
          buyer_email: invoice.buyer_email || invoice.client_email,
          currency: invoice.currency as FormValues["currency"],
          due_date: invoice.due_date,
          notes: invoice.notes || "",
          items: invoice.items.map((i) => ({
            description: i.description,
            quantity: i.quantity,
            unit_price: i.unit_price,
            tax_rate: i.tax_rate,
          })),
        });
      })
      .catch((e) => setMessage(getApiError(e)));
  }, [editId, form]);

  const watched = form.watch();
  const total = useMemo(() => {
    return watched.items.reduce((sum, item) => sum + item.quantity * item.unit_price * (1 + item.tax_rate / 100), 0);
  }, [watched.items]);

  async function onSubmit(values: FormValues) {
    try {
      setLoading(true);
      setMessage("");
      if (editId) {
        await updateInvoice(editId, {
          seller_name: values.seller_name,
          seller_address: values.seller_address,
          seller_email: values.seller_email,
          buyer_name: values.buyer_name,
          buyer_address: values.buyer_address,
          buyer_email: values.buyer_email,
          currency: values.currency,
          due_date: values.due_date,
          notes: values.notes,
        });
        setMessage("Invoice updated successfully.");
      } else {
        await createInvoice({
          ...values,
          items: values.items.map((item, index) => ({
            item_number: String(index + 1),
            description: item.description,
            quantity: item.quantity,
            unit_price: item.unit_price,
            tax_rate: item.tax_rate,
          })),
        });
        if (selectedClientId === "__new__") {
          await createClient({
            name: values.buyer_name,
            email: values.buyer_email,
            address: values.buyer_address,
            currency: values.currency,
          });
        }
        setMessage("Invoice created successfully.");
        form.reset();
      }
    } catch (e) {
      setMessage(getApiError(e));
    } finally {
      setLoading(false);
    }
  }

  return (
    <PageTransition>
      <div className="grid gap-6 lg:grid-cols-[1.4fr_1fr]">
        <Card>
          <CardHeader>
            <CardTitle>{editId ? "Edit invoice" : "Compose invoice"}</CardTitle>
          </CardHeader>
          <CardContent>
            <form className="space-y-4" onSubmit={form.handleSubmit(onSubmit)}>
              {!editId ? (
                <div className="grid gap-3 md:grid-cols-2">
                  <div>
                    <label className="muted-text">Load client profile</label>
                    <select
                      className="h-10 w-full rounded-2xl border border-input bg-background px-3 text-sm"
                      value={selectedClientId}
                      onChange={(e) => {
                        const value = e.target.value;
                        setSelectedClientId(value);
                        const chosen = clients.find((c) => c.client_id === value);
                        if (chosen) {
                          form.setValue("buyer_name", chosen.name);
                          form.setValue("buyer_email", chosen.email);
                          form.setValue("buyer_address", chosen.address || "");
                          form.setValue("currency", (chosen.currency as FormValues["currency"]) || "AUD");
                        }
                      }}
                    >
                      <option value="">Select a saved client</option>
                      {clients.map((client) => (
                        <option key={client.client_id} value={client.client_id}>
                          {client.name} - {client.email}
                        </option>
                      ))}
                      <option value="__new__">Use current buyer as new saved client on submit</option>
                    </select>
                  </div>
                  <div>
                    <label className="muted-text">Apply template</label>
                    <select
                      className="h-10 w-full rounded-2xl border border-input bg-background px-3 text-sm"
                      value={selectedTemplateId}
                      onChange={(e) => {
                        const value = e.target.value;
                        setSelectedTemplateId(value);
                        const chosen = templates.find((t) => t.template_id === value);
                        if (chosen?.payment_terms_text) {
                          form.setValue("notes", chosen.payment_terms_text);
                        }
                      }}
                    >
                      <option value="">No template</option>
                      {templates.map((template) => (
                        <option key={template.template_id} value={template.template_id}>
                          {template.name}
                        </option>
                      ))}
                    </select>
                  </div>
                </div>
              ) : null}

              <div className="grid gap-3 md:grid-cols-2">
                <div>
                  <label className="muted-text">Seller name</label>
                  <Input {...form.register("seller_name")} />
                </div>
                <div>
                  <label className="muted-text">Seller email</label>
                  <Input {...form.register("seller_email")} />
                </div>
                <div className="md:col-span-2">
                  <label className="muted-text">Seller address</label>
                  <Input {...form.register("seller_address")} />
                </div>
                <div>
                  <label className="muted-text">Buyer name</label>
                  <Input {...form.register("buyer_name")} />
                </div>
                <div>
                  <label className="muted-text">Buyer email</label>
                  <Input {...form.register("buyer_email")} />
                </div>
                <div className="md:col-span-2">
                  <label className="muted-text">Buyer address</label>
                  <Input {...form.register("buyer_address")} />
                </div>
                <div>
                  <label className="muted-text">Due date</label>
                  <Input type="date" {...form.register("due_date")} />
                </div>
                <div>
                  <label className="muted-text">Currency</label>
                  <select className="h-10 w-full rounded-2xl border border-input bg-background px-3 text-sm" {...form.register("currency")}>
                    <option value="AUD">AUD</option>
                    <option value="USD">USD</option>
                    <option value="GBP">GBP</option>
                    <option value="EUR">EUR</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="muted-text">Notes</label>
                <Textarea rows={4} {...form.register("notes")} />
              </div>

              <div className="space-y-3">
                {fields.map((field, index) => (
                  <div key={field.id} className="grid gap-2 rounded-xl border border-border p-3 md:grid-cols-4">
                    <Input placeholder="Description" {...form.register(`items.${index}.description`)} />
                    <Input type="number" step="1" {...form.register(`items.${index}.quantity`)} />
                    <Input type="number" step="0.01" {...form.register(`items.${index}.unit_price`)} />
                    <div className="flex gap-2">
                      <Input type="number" step="0.1" {...form.register(`items.${index}.tax_rate`)} />
                      <Button type="button" variant="ghost" onClick={() => remove(index)} disabled={fields.length === 1}>
                        Remove
                      </Button>
                    </div>
                  </div>
                ))}
              </div>

              <div className="flex gap-2">
                <Button type="button" variant="secondary" onClick={() => append({ description: "", quantity: 1, unit_price: 0, tax_rate: 10 })}>
                  Add Line
                </Button>
                <Button type="submit" disabled={loading}>
                  {loading ? "Saving..." : editId ? "Save changes" : "Create invoice"}
                </Button>
              </div>
              {message ? <p className="muted-text">{message}</p> : null}
            </form>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Email preview</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            <p className="text-sm">Hi {watched.buyer_name || "Client"},</p>
            <p className="text-sm text-muted-foreground">
              Your invoice is ready. Please use the import link in the email body to view or process your invoice.
            </p>
            <div className="rounded-xl bg-cream p-3 text-sm">
              <p>Invoice total: {watched.currency} {total.toFixed(2)}</p>
              <p>Due date: {watched.due_date || "-"}</p>
              <p>Items: {watched.items.length}</p>
            </div>
            <p className="text-xs text-muted-foreground">This is a live preview of the email tone and summary.</p>
          </CardContent>
        </Card>
      </div>
    </PageTransition>
  );
}
