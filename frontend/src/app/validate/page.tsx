"use client";

import { FormEvent, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { fetchInvoice, fetchInvoices, getApiError } from "@/lib/api";
import type { Invoice } from "@/lib/types";
import { PageTransition } from "@/components/page-transition";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Input } from "@/components/ui/input";

type ValidationIssue = {
  rule: string;
  severity: string;
  description: string;
};

type ValidationResult = {
  valid: boolean;
  ruleset: string;
  errors: ValidationIssue[];
};

export default function ValidatePage() {
  const params = useSearchParams();
  const [ruleset, setRuleset] = useState<"ubl" | "peppol" | "australian">("ubl");
  const [sourceMode, setSourceMode] = useState<"paste" | "upload" | "library">("paste");
  const [invoiceXml, setInvoiceXml] = useState("");
  const [invoices, setInvoices] = useState<Invoice[]>([]);
  const [selectedInvoiceId, setSelectedInvoiceId] = useState("");
  const [loadingInvoices, setLoadingInvoices] = useState(false);
  const [result, setResult] = useState<ValidationResult | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    setLoadingInvoices(true);
    fetchInvoices({ page_size: 100, sort_by: "created_at", sort_order: "desc" })
      .then(setInvoices)
      .catch((e) => setError(getApiError(e)))
      .finally(() => setLoadingInvoices(false));
  }, []);

  async function loadInvoiceXml(invoiceId: string) {
    try {
      setError("");
      const data = await fetchInvoice(invoiceId, "ubl");
      if (typeof data !== "string") {
        throw new Error("Selected invoice could not be loaded as XML.");
      }
      setInvoiceXml(data);
    } catch (e) {
      setError(getApiError(e));
    }
  }

  useEffect(() => {
    const invoiceId = params?.get("invoiceId");
    const xmlParam = params?.get("xml");
    if (xmlParam) {
      setSourceMode("paste");
      setInvoiceXml(xmlParam);
      return;
    }
    if (!invoiceId) return;
    setSourceMode("library");
    setSelectedInvoiceId(invoiceId);
    void loadInvoiceXml(invoiceId);
  }, [params]);

  async function onXmlUpload(file: File | null) {
    if (!file) return;
    try {
      setError("");
      const text = await file.text();
      if (!text.trim()) {
        setError("Uploaded XML file is empty.");
        return;
      }
      setSourceMode("upload");
      setInvoiceXml(text);
    } catch {
      setError("Could not read the uploaded XML file.");
    }
  }

  async function handleValidate(e: FormEvent) {
    e.preventDefault();
    setError("");
    setResult(null);

    try {
      setLoading(true);
      const response = await fetch("/api/validate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ invoice_xml: invoiceXml, ruleset }),
      });

      const data = (await response.json()) as ValidationResult | { detail?: string };
      if (!response.ok) {
        throw new Error("detail" in data ? data.detail || "Validation failed." : "Validation failed.");
      }
      setResult(data as ValidationResult);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Validation failed.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <PageTransition>
      <div className="space-y-6">
        <div>
          <h2 className="text-2xl font-semibold">Validate</h2>
          <p className="muted-text">Validate UBL XML invoices with UBL, PEPPOL or Australian rules.</p>
        </div>

        <Card>
          <CardHeader>
            <CardTitle>Validation tool</CardTitle>
            <CardDescription>Paste XML, upload an XML file, or load an invoice from your library.</CardDescription>
          </CardHeader>
          <CardContent>
            <form className="space-y-4" onSubmit={handleValidate}>
              <div className="grid gap-4 md:grid-cols-2">
                <div>
                  <label className="muted-text">Source</label>
                  <select
                    className="h-10 w-full rounded-2xl border border-input bg-background px-3 text-sm"
                    value={sourceMode}
                    onChange={(e) => setSourceMode(e.target.value as "paste" | "upload" | "library")}
                  >
                    <option value="paste">Paste XML</option>
                    <option value="upload">Upload XML file</option>
                    <option value="library">Select invoice from library</option>
                  </select>
                </div>
                <div>
                  <label className="muted-text">Ruleset</label>
                  <select
                    className="h-10 w-full rounded-2xl border border-input bg-background px-3 text-sm"
                    value={ruleset}
                    onChange={(e) => setRuleset(e.target.value as "ubl" | "peppol" | "australian")}
                  >
                    <option value="ubl">ubl</option>
                    <option value="peppol">peppol</option>
                    <option value="australian">australian</option>
                  </select>
                </div>
              </div>

              {sourceMode === "upload" ? (
                <div>
                  <label className="muted-text">Upload XML file</label>
                  <Input type="file" accept=".xml,text/xml,application/xml" onChange={(e) => onXmlUpload(e.target.files?.[0] || null)} />
                </div>
              ) : null}

              {sourceMode === "library" ? (
                <div>
                  <label className="muted-text">Invoice from library</label>
                  <select
                    className="h-10 w-full rounded-2xl border border-input bg-background px-3 text-sm"
                    value={selectedInvoiceId}
                    onChange={(e) => {
                      const invoiceId = e.target.value;
                      setSelectedInvoiceId(invoiceId);
                      if (invoiceId) void loadInvoiceXml(invoiceId);
                    }}
                  >
                    <option value="">{loadingInvoices ? "Loading invoices..." : "Select an invoice"}</option>
                    {invoices.map((invoice) => (
                      <option key={invoice.invoice_id} value={invoice.invoice_id}>
                        {invoice.invoice_number} - {invoice.buyer_name || invoice.client_name}
                      </option>
                    ))}
                  </select>
                </div>
              ) : null}

              <div>
                <label className="muted-text">Invoice XML</label>
                <Textarea
                  rows={16}
                  value={invoiceXml}
                  onChange={(e) => setInvoiceXml(e.target.value)}
                  placeholder="Paste UBL XML here..."
                />
              </div>
              <div className="flex gap-2">
                <Button type="submit" disabled={loading}>
                  {loading ? "Validating..." : "Validate invoice"}
                </Button>
                <Button type="button" variant="secondary" onClick={() => { setInvoiceXml(""); setResult(null); }}>
                  Clear
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>

        {error ? (
          <Card>
            <CardContent className="p-5">
              <p className="text-sm text-rose-700">{error}</p>
            </CardContent>
          </Card>
        ) : null}

        {result ? (
          <Card>
            <CardHeader>
              <CardTitle>Validation result</CardTitle>
              <CardDescription>
                Ruleset: {result.ruleset} | Status: {result.valid ? "Valid" : "Invalid"}
              </CardDescription>
            </CardHeader>
            <CardContent>
              {result.errors.length === 0 ? (
                <p className="muted-text">No errors found.</p>
              ) : (
                <div className="space-y-2">
                  {result.errors.map((issue, idx) => (
                    <div key={`${issue.rule}-${idx}`} className="rounded-xl border border-border p-3">
                      <p className="text-sm font-medium">
                        {issue.rule} - {issue.severity}
                      </p>
                      <p className="muted-text">{issue.description}</p>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        ) : null}
      </div>
    </PageTransition>
  );
}
