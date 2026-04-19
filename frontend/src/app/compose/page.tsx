"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useSearchParams } from "next/navigation";
import { useFieldArray, useForm, useWatch } from "react-hook-form";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import { Upload } from "lucide-react";
import {
  API_BASE,
  createInvoice,
  fetchClients,
  fetchInvoice,
  fetchTemplates,
  getApiError,
  getStoredToken,
  parseInvoiceFile,
  sendInvoiceWithImportLink,
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
  issue_date: z.string().optional(),
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
  const [outputFormat, setOutputFormat] = useState("json");
  const [lastInvoiceId, setLastInvoiceId] = useState("");
  const [sendEmail, setSendEmail] = useState("");
  const [clients, setClients] = useState<Client[]>([]);
  const [templates, setTemplates] = useState<Template[]>([]);
  const [selectedClientId, setSelectedClientId] = useState("");
  const [selectedTemplateId, setSelectedTemplateId] = useState("");
  const [importLoading, setImportLoading] = useState(false);
  const [importMessage, setImportMessage] = useState("");
  const importFileRef = useRef<HTMLInputElement>(null);

  const VALID_CURRENCIES = ["AUD", "USD", "GBP", "EUR"] as const;

  function applyParsedData(parsed: Record<string, unknown>) {
    const str = (v: unknown) => (v != null ? String(v).trim() : "");
    const num = (v: unknown) => {
      const n = parseFloat(String(v ?? "0"));
      return isNaN(n) ? 0 : n;
    };
    const currency = str(parsed.currency).toUpperCase();

    const rawItems = Array.isArray(parsed.items) ? parsed.items : [];
    const mappedItems = rawItems
      .filter((it: unknown) => it && typeof it === "object")
      .map((it: unknown) => {
        const item = it as Record<string, unknown>;
        return {
          description: str(item.description) || "Item",
          quantity: Math.max(1, num(item.quantity)),
          unit_price: num(item.unit_price),
          tax_rate: num(item.tax_rate) || 10,
        };
      });

    form.reset({
      seller_name: str(parsed.seller_name),
      seller_address: str(parsed.seller_address),
      seller_email: str(parsed.seller_email),
      buyer_name: str(parsed.buyer_name),
      buyer_address: str(parsed.buyer_address),
      buyer_email: str(parsed.buyer_email),
      currency: (VALID_CURRENCIES.includes(currency as "AUD") ? currency : "AUD") as FormValues["currency"],
      issue_date: str(parsed.issue_date),
      due_date: str(parsed.due_date),
      notes: str(parsed.notes),
      items: mappedItems.length > 0 ? mappedItems : [{ description: "", quantity: 1, unit_price: 0, tax_rate: 10 }],
    });
  }

  async function handleImportFile(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    e.target.value = "";
    try {
      setImportLoading(true);
      setImportMessage("");
      const parsed = await parseInvoiceFile(file);
      applyParsedData(parsed);
      setImportMessage(`Imported from "${file.name}". Review and adjust before saving.`);
    } catch (err) {
      setImportMessage(getApiError(err));
    } finally {
      setImportLoading(false);
    }
  }

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
      issue_date: "",
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

    // Pre-fill from file import initiated on the invoices list page
    const stored = sessionStorage.getItem("invoice_import_data");
    if (stored) {
      try {
        const parsed = JSON.parse(stored) as Record<string, unknown>;
        applyParsedData(parsed);
        setImportMessage("Form pre-filled from imported file. Review before saving.");
      } catch {
        // ignore corrupt data
      } finally {
        sessionStorage.removeItem("invoice_import_data");
      }
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
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
          issue_date: invoice.issue_date ?? "",
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
  const watchedItems = useWatch({ control: form.control, name: "items" }) || [];
  const watchedCurrency = useWatch({ control: form.control, name: "currency" }) || "AUD";
  const pricedItems = useMemo(() => {
    return watchedItems.map((item) => {
      const quantity = Number(item?.quantity || 0);
      const unitPrice = Number(item?.unit_price || 0);
      const taxRate = Number(item?.tax_rate || 0);
      const lineSubtotal = quantity * unitPrice;
      const taxAmount = lineSubtotal * (taxRate / 100);
      const lineTotal = lineSubtotal + taxAmount;
      return {
        description: item?.description || "",
        quantity,
        unitPrice,
        taxRate,
        lineSubtotal,
        taxAmount,
        lineTotal,
      };
    });
  }, [watchedItems]);

  const subtotal = useMemo(() => {
    return pricedItems.reduce((sum, item) => sum + item.lineSubtotal, 0);
  }, [pricedItems]);

  const taxTotal = useMemo(() => {
    return pricedItems.reduce((sum, item) => sum + item.taxAmount, 0);
  }, [pricedItems]);

  const grandTotal = useMemo(() => {
    return subtotal + taxTotal;
  }, [subtotal, taxTotal]);

  async function downloadInvoice(invoiceId: string, format: string) {
    const token = getStoredToken();
    const resp = await fetch(`${API_BASE}/invoice/fetch/${invoiceId}?format=${format}`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    });
    if (!resp.ok) throw new Error("Download failed.");
    const blob = await resp.blob();
    const ext = format === "ubl_xml" ? "xml" : format;
    const objectUrl = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = objectUrl;
    a.download = `invoice-${invoiceId}.${ext}`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(objectUrl);
  }

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
          issue_date: values.issue_date || undefined,
          due_date: values.due_date,
          notes: values.notes,
          items: values.items.map((item, index) => ({
            item_number: String(index + 1),
            description: item.description,
            quantity: item.quantity,
            unit_price: item.unit_price,
            tax_rate: item.tax_rate,
          })),
        });
        setMessage("Invoice updated successfully.");
      } else {
        const created = await createInvoice({
          ...values,
          issue_date: values.issue_date || undefined,
          items: values.items.map((item, index) => ({
            item_number: String(index + 1),
            description: item.description,
            quantity: item.quantity,
            unit_price: item.unit_price,
            tax_rate: item.tax_rate,
          })),
        });
        setLastInvoiceId(created?.invoice_id || "");
        if (outputFormat !== "json" && created?.invoice_id) {
          await downloadInvoice(created.invoice_id, outputFormat);
          setMessage(`Invoice created and downloaded as ${outputFormat.toUpperCase()}. You can now send it to the client below.`);
        } else {
          setMessage("Invoice created successfully. You can now send it to the client below.");
        }
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
            {/* File import bar */}
            <div className="mb-4 flex flex-wrap items-center gap-3 rounded-xl border border-dashed border-input bg-muted/40 px-4 py-3">
              <Upload className="h-4 w-4 text-muted-foreground shrink-0" />
              <p className="text-sm text-muted-foreground flex-1">
                Have an existing invoice file? Import it to pre-fill this form.
              </p>
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
                size="sm"
                disabled={importLoading}
                onClick={() => importFileRef.current?.click()}
              >
                {importLoading ? "Importing…" : "Import from file"}
              </Button>
              {importMessage ? (
                <p className={`w-full text-xs ${importMessage.toLowerCase().includes("error") || importMessage.toLowerCase().includes("could not") || importMessage.toLowerCase().includes("network") ? "text-rose-600" : "text-green-600"}`}>
                  {importMessage}
                </p>
              ) : null}
            </div>
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
                  <label className="muted-text">Issue date</label>
                  <Input type="date" {...form.register("issue_date")} />
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
                <div className="hidden gap-2 px-1 text-xs font-medium text-muted-foreground md:grid md:grid-cols-6">
                  <p>Description</p>
                  <p>Quantity</p>
                  <p>Unit Price</p>
                  <p>Tax %</p>
                  <p>Total</p>
                  <p>Action</p>
                </div>
                {fields.map((field, index) => (
                  <div key={field.id} className="grid gap-2 rounded-xl border border-border p-3 md:grid-cols-6">
                    <Input placeholder="Description" {...form.register(`items.${index}.description`)} />
                    <Input type="number" step="1" {...form.register(`items.${index}.quantity`)} />
                    <Input type="number" step="0.01" {...form.register(`items.${index}.unit_price`)} />
                    <Input type="number" step="0.1" {...form.register(`items.${index}.tax_rate`)} />
                    <div className="flex items-center rounded-2xl border border-input bg-background px-3 text-sm">
                      {watchedCurrency} {pricedItems[index]?.lineTotal.toFixed(2) || "0.00"}
                    </div>
                    <div className="flex items-center">
                      <Button type="button" variant="ghost" onClick={() => remove(index)} disabled={fields.length === 1}>
                        Remove
                      </Button>
                    </div>
                  </div>
                ))}
              </div>

              <div className="flex flex-wrap items-end gap-2">
                <Button type="button" variant="secondary" onClick={() => append({ description: "", quantity: 1, unit_price: 0, tax_rate: 10 })}>
                  Add Line
                </Button>
                {!editId ? (
                  <div className="flex items-center gap-2">
                    <label className="muted-text whitespace-nowrap">Download as</label>
                    <select
                      className="h-10 rounded-2xl border border-input bg-background px-3 text-sm"
                      value={outputFormat}
                      onChange={(e) => setOutputFormat(e.target.value)}
                    >
                      <option value="json">JSON</option>
                      <option value="pdf">PDF</option>
                      <option value="csv">CSV</option>
                      <option value="xml">XML</option>
                      <option value="ubl_xml">UBL XML</option>
                    </select>
                  </div>
                ) : null}
                <Button type="submit" disabled={loading}>
                  {loading ? "Saving..." : editId ? "Save changes" : "Create invoice"}
                </Button>
              </div>
              {message ? <p className="muted-text">{message}</p> : null}

              {/* Send to client — shown after a new invoice is created */}
              {lastInvoiceId && !editId ? (
                <div className="rounded-xl border border-border bg-background p-4 space-y-3">
                  <p className="text-sm font-medium">Send to client</p>
                  <div className="flex gap-2">
                    <Input
                      type="email"
                      placeholder="Recipient email address"
                      value={sendEmail}
                      onChange={(e) => setSendEmail(e.target.value)}
                    />
                    <Button
                      type="button"
                      disabled={loading || !sendEmail}
                      onClick={async () => {
                        try {
                          setLoading(true);
                          await sendInvoiceWithImportLink(lastInvoiceId, sendEmail);
                          setMessage(`Invoice email sent to ${sendEmail}.`);
                          setSendEmail("");
                        } catch (e) {
                          setMessage(getApiError(e));
                        } finally {
                          setLoading(false);
                        }
                      }}
                    >
                      Send email
                    </Button>
                  </div>
                </div>
              ) : null}
            </form>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Email preview</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4 text-sm">
            <p>Hi {watched.buyer_name || "Client"},</p>
            <p className="text-muted-foreground">Please find your invoice details below.</p>

            <div className="rounded-xl border border-border bg-cream/40 p-4">
              <div className="mb-4 flex items-start justify-between">
                <div>
                  <p className="text-xs uppercase tracking-wide text-muted-foreground">Seller</p>
                  <p className="font-medium">{watched.seller_name || "-"}</p>
                  <p className="text-muted-foreground">{watched.seller_email || "-"}</p>
                  <p className="text-muted-foreground">{watched.seller_address || "-"}</p>
                </div>
                <div className="text-right">
                  <p className="text-xs uppercase tracking-wide text-muted-foreground">Buyer</p>
                  <p className="font-medium">{watched.buyer_name || "-"}</p>
                  <p className="text-muted-foreground">{watched.buyer_email || "-"}</p>
                  <p className="text-muted-foreground">{watched.buyer_address || "-"}</p>
                </div>
              </div>

              <div className="mb-3 overflow-x-auto rounded-xl border border-border bg-background">
                <table className="w-full text-xs">
                  <colgroup>
                    <col style={{ width: "40%" }} />
                    <col style={{ width: "12%" }} />
                    <col style={{ width: "18%" }} />
                    <col style={{ width: "10%" }} />
                    <col style={{ width: "20%" }} />
                  </colgroup>
                  <thead>
                    <tr className="border-b border-border text-muted-foreground">
                      <th className="px-3 py-2 text-left font-medium">Description</th>
                      <th className="px-2 py-2 text-right font-medium">Qty</th>
                      <th className="px-2 py-2 text-right font-medium">Unit Price</th>
                      <th className="px-2 py-2 text-right font-medium">Tax %</th>
                      <th className="px-3 py-2 text-right font-medium">Line Total</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border">
                    {pricedItems.map((item, idx) => (
                      <tr key={`${item.description}-${idx}`}>
                        <td className="px-3 py-2">{item.description || `Item ${idx + 1}`}</td>
                        <td className="px-2 py-2 text-right">{item.quantity}</td>
                        <td className="px-2 py-2 text-right">
                          {watchedCurrency} {item.unitPrice.toFixed(2)}
                        </td>
                        <td className="px-2 py-2 text-right">{item.taxRate}%</td>
                        <td className="px-3 py-2 text-right font-medium">
                          {watchedCurrency} {item.lineTotal.toFixed(2)}
                        </td>
                      </tr>
                    ))}
                    {pricedItems.length === 0 ? (
                      <tr>
                        <td colSpan={5} className="px-3 py-3 text-muted-foreground">
                          No line items yet.
                        </td>
                      </tr>
                    ) : null}
                  </tbody>
                </table>
              </div>

              <div className="space-y-1 text-right">
                <p className="text-muted-foreground">
                  Subtotal: {watchedCurrency} {subtotal.toFixed(2)}
                </p>
                <p className="text-muted-foreground">
                  Tax total: {watchedCurrency} {taxTotal.toFixed(2)}
                </p>
                <p className="text-base font-semibold">
                  Grand total: {watchedCurrency} {grandTotal.toFixed(2)}
                </p>
                <p className="text-xs text-muted-foreground">Due date: {watched.due_date || "-"}</p>
              </div>
            </div>
            <p className="text-xs text-muted-foreground">This preview updates live as you edit fields.</p>
          </CardContent>
        </Card>
      </div>
    </PageTransition>
  );
}
