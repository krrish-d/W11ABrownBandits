"use client";

import { FormEvent, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { PageTransition } from "@/components/page-transition";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { fetchInvoice, getApiError, getStoredToken } from "@/lib/api";
import type { Invoice } from "@/lib/types";

const FORMATS = ["json", "csv", "xml", "ubl_xml", "pdf"] as const;

function readFileAsText(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result || ""));
    reader.onerror = () => reject(new Error("Could not read the file."));
    reader.readAsText(file);
  });
}

function toBase64(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => {
      const value = String(reader.result || "");
      const base64 = value.includes(",") ? value.split(",")[1] : value;
      resolve(base64);
    };
    reader.onerror = () => reject(new Error("Could not read the file."));
    reader.readAsDataURL(file);
  });
}

function triggerDownload(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

export default function TransformPage() {
  const params = useSearchParams();
  const invoiceId = params?.get("invoiceId");

  const [inputFormat, setInputFormat] = useState<(typeof FORMATS)[number]>("json");
  const [outputFormat, setOutputFormat] = useState<(typeof FORMATS)[number]>("ubl_xml");
  const [xmlType, setXmlType] = useState<"ubl" | "generic">("ubl");
  const [invoiceData, setInvoiceData] = useState("");
  const [uploadedFile, setUploadedFile] = useState<File | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Result state — only json shows inline text, everything else triggers a download
  const [resultJson, setResultJson] = useState("");
  const [lastOutputFormat, setLastOutputFormat] = useState<string>("");
  const [lastXml, setLastXml] = useState("");  // stored for "Validate" link

  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [preloading, setPreloading] = useState(false);

  // Preload invoice JSON when opened from the invoice list row
  useEffect(() => {
    if (!invoiceId) return;
    let cancelled = false;
    setPreloading(true);
    fetchInvoice(invoiceId, "json")
      .then((data) => {
        if (cancelled) return;
        setInputFormat("json");
        setInvoiceData(JSON.stringify(data as Invoice, null, 2));
      })
      .catch((e) => {
        if (cancelled) return;
        setError(getApiError(e));
      })
      .finally(() => {
        if (!cancelled) setPreloading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [invoiceId]);

  async function onFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0] ?? null;
    setUploadedFile(file);
    if (!file) return;

    if (inputFormat === "pdf") return; // PDF is sent as base64, not text

    try {
      const text = await readFileAsText(file);
      setInvoiceData(text);
    } catch {
      setError("Could not read the uploaded file.");
    }
  }

  function clearFile() {
    setUploadedFile(null);
    if (fileInputRef.current) fileInputRef.current.value = "";
  }

  function resetResult() {
    setResultJson("");
    setLastOutputFormat("");
    setLastXml("");
    setError("");
  }

  async function handleTransform(e: FormEvent) {
    e.preventDefault();
    resetResult();

    try {
      setLoading(true);
      const token = getStoredToken();
      const headers: Record<string, string> = { "Content-Type": "application/json" };
      if (token) headers["Authorization"] = `Bearer ${token}`;

      const payload: Record<string, string> = {
        input_format: inputFormat,
        output_format: outputFormat,
        xml_type: xmlType,
      };

      if (inputFormat === "pdf") {
        if (!uploadedFile) {
          setError("Please upload a PDF file to transform.");
          return;
        }
        payload.invoice_data_base64 = await toBase64(uploadedFile);
      } else {
        if (!invoiceData.trim()) {
          setError("Please provide invoice data.");
          return;
        }
        payload.invoice_data = invoiceData;
      }

      const response = await fetch("/api/transform", {
        method: "POST",
        headers,
        body: JSON.stringify(payload),
      });

      const contentType = response.headers.get("content-type") || "";
      if (!response.ok) {
        if (contentType.includes("application/json")) {
          const data = (await response.json()) as { detail?: string };
          throw new Error(data.detail || "Transformation failed.");
        }
        throw new Error(await response.text());
      }

      setLastOutputFormat(outputFormat);

      if (outputFormat === "pdf" || contentType.includes("application/pdf")) {
        const blob = await response.blob();
        triggerDownload(blob, "invoice.pdf");
        return;
      }

      if (outputFormat === "csv" || contentType.includes("text/csv")) {
        const blob = await response.blob();
        triggerDownload(blob, "invoice.csv");
        return;
      }

      if (outputFormat === "ubl_xml" || outputFormat === "xml" || contentType.includes("application/xml")) {
        const text = await response.text();
        setLastXml(text);
        const blob = new Blob([text], { type: "application/xml" });
        triggerDownload(blob, `invoice.xml`);
        return;
      }

      // JSON
      if (contentType.includes("application/json")) {
        const data = (await response.json()) as { converted_invoice?: unknown };
        const value = data.converted_invoice ?? data;
        setResultJson(typeof value === "string" ? value : JSON.stringify(value, null, 2));
        return;
      }

      const rawText = await response.text();
      setResultJson(rawText);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Transformation failed.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <PageTransition>
      <div className="space-y-6">
        <div>
          <h2 className="text-2xl font-semibold">Transform</h2>
          <p className="muted-text">Convert invoice data between JSON, XML, UBL, CSV and PDF.</p>
          {invoiceId ? (
            <p className="mt-1 text-xs text-muted-foreground">
              {preloading ? "Loading invoice…" : `Loaded invoice ${invoiceId} — edit or transform below.`}
            </p>
          ) : null}
        </div>

        <Card>
          <CardHeader>
            <CardTitle>Transformation tool</CardTitle>
            <CardDescription>
              Upload a file or paste text. Non-JSON results are downloaded automatically.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form className="space-y-4" onSubmit={handleTransform}>
              <div className="grid gap-4 md:grid-cols-3">
                <div>
                  <label className="muted-text">Input format</label>
                  <select
                    className="h-10 w-full rounded-2xl border border-input bg-background px-3 text-sm"
                    value={inputFormat}
                    onChange={(e) => {
                      setInputFormat(e.target.value as (typeof FORMATS)[number]);
                      clearFile();
                    }}
                  >
                    {FORMATS.map((f) => (
                      <option key={f} value={f}>
                        {f}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="muted-text">Output format</label>
                  <select
                    className="h-10 w-full rounded-2xl border border-input bg-background px-3 text-sm"
                    value={outputFormat}
                    onChange={(e) => setOutputFormat(e.target.value as (typeof FORMATS)[number])}
                  >
                    {FORMATS.map((f) => (
                      <option key={f} value={f}>
                        {f}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="muted-text">XML output type</label>
                  <select
                    className="h-10 w-full rounded-2xl border border-input bg-background px-3 text-sm"
                    value={xmlType}
                    onChange={(e) => setXmlType(e.target.value as "ubl" | "generic")}
                  >
                    <option value="ubl">ubl</option>
                    <option value="generic">generic</option>
                  </select>
                </div>
              </div>

              {/* File upload for all formats */}
              <div>
                <label className="muted-text">
                  {inputFormat === "pdf"
                    ? "PDF file (required)"
                    : "Upload file (optional — fills the text box below)"}
                </label>
                <div className="flex items-center gap-2">
                  <Input
                    ref={fileInputRef}
                    type="file"
                    accept={
                      inputFormat === "pdf"
                        ? "application/pdf"
                        : inputFormat === "csv"
                          ? ".csv,text/csv"
                          : inputFormat === "json"
                            ? ".json,application/json"
                            : ".xml,text/xml,application/xml"
                    }
                    onChange={onFileChange}
                  />
                  {uploadedFile ? (
                    <Button type="button" variant="ghost" onClick={clearFile} className="shrink-0">
                      Clear
                    </Button>
                  ) : null}
                </div>
                {uploadedFile && inputFormat !== "pdf" ? (
                  <p className="mt-1 text-xs text-muted-foreground">
                    File contents loaded below — edit before transforming if needed.
                  </p>
                ) : null}
              </div>

              {/* Text area for non-PDF input */}
              {inputFormat !== "pdf" ? (
                <div>
                  <label className="muted-text">Invoice data</label>
                  <Textarea
                    rows={14}
                    value={invoiceData}
                    onChange={(e) => setInvoiceData(e.target.value)}
                    placeholder="Paste JSON, XML, CSV or UBL invoice content here…"
                  />
                </div>
              ) : null}

              <div className="flex gap-2">
                <Button type="submit" disabled={loading || preloading}>
                  {loading ? "Transforming..." : "Transform invoice"}
                </Button>
                {inputFormat !== "pdf" ? (
                  <Button
                    type="button"
                    variant="secondary"
                    onClick={() => {
                      setInvoiceData("");
                      clearFile();
                      resetResult();
                    }}
                  >
                    Clear
                  </Button>
                ) : null}
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

        {/* Success notice for downloaded files */}
        {!error && lastOutputFormat && lastOutputFormat !== "json" ? (
          <Card>
            <CardHeader>
              <CardTitle>Result</CardTitle>
              <CardDescription>
                Your {lastOutputFormat.toUpperCase()} file has been downloaded.
              </CardDescription>
            </CardHeader>
            <CardContent className="flex flex-wrap gap-2">
              {/* Offer to validate XML/UBL output */}
              {(lastOutputFormat === "ubl_xml" || lastOutputFormat === "xml") && lastXml ? (
                <Link
                  href={`/validate?xml=${encodeURIComponent(lastXml.slice(0, 4000))}`}
                >
                  <Button variant="secondary">Validate this XML</Button>
                </Link>
              ) : null}
              <Button variant="secondary" onClick={resetResult}>
                Clear
              </Button>
            </CardContent>
          </Card>
        ) : null}

        {/* Inline result for JSON output */}
        {resultJson ? (
          <Card>
            <CardHeader>
              <CardTitle>Result — JSON</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              <Textarea readOnly rows={16} value={resultJson} />
              <Button variant="secondary" onClick={resetResult}>
                Clear
              </Button>
            </CardContent>
          </Card>
        ) : null}
      </div>
    </PageTransition>
  );
}
