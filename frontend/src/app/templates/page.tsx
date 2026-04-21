"use client";

import { useEffect, useState } from "react";
import { createTemplate, fetchTemplates, getApiError } from "@/lib/api";
import type { Template } from "@/lib/types";
import { PageTransition } from "@/components/page-transition";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";

function ColourPicker({
  label,
  description,
  value,
  onChange,
}: {
  label: string;
  description: string;
  value: string;
  onChange: (v: string) => void;
}) {
  return (
    <div className="space-y-1">
      <label className="text-sm font-medium">{label}</label>
      <p className="text-xs text-muted-foreground">{description}</p>
      <div className="flex items-center gap-3">
        <input
          type="color"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          className="h-10 w-14 cursor-pointer rounded-lg border border-input bg-background p-1"
        />
        <Input
          className="w-32 font-mono text-sm"
          value={value}
          maxLength={7}
          onChange={(e) => {
            const v = e.target.value;
            if (/^#[0-9a-fA-F]{0,6}$/.test(v)) onChange(v);
          }}
        />
        <span
          className="h-8 w-8 rounded-full border border-input"
          style={{ background: value }}
        />
      </div>
    </div>
  );
}

export default function TemplatesPage() {
  const [templates, setTemplates] = useState<Template[]>([]);
  const [message, setMessage] = useState("");
  const [messageIsError, setMessageIsError] = useState(false);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [form, setForm] = useState({
    name: "",
    primary_colour: "#2563eb",
    secondary_colour: "#1e40af",
    footer_text: "",
    payment_terms_text: "",
    bank_details: "",
    is_default: false,
  });

  async function loadTemplates() {
    try {
      setLoading(true);
      const data = await fetchTemplates();
      setTemplates(data);
    } catch (error) {
      setMessage(getApiError(error));
      setMessageIsError(true);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadTemplates();
  }, []);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    try {
      setMessage("");
      setMessageIsError(false);
      setSaving(true);
      await createTemplate({
        name: form.name,
        primary_colour: form.primary_colour,
        secondary_colour: form.secondary_colour,
        footer_text: form.footer_text || undefined,
        payment_terms_text: form.payment_terms_text || undefined,
        bank_details: form.bank_details || undefined,
        is_default: form.is_default,
      });
      setForm({
        name: "",
        primary_colour: "#2563eb",
        secondary_colour: "#1e40af",
        footer_text: "",
        payment_terms_text: "",
        bank_details: "",
        is_default: false,
      });
      setMessage("Template saved successfully.");
      setMessageIsError(false);
      await loadTemplates();
    } catch (error) {
      setMessage(getApiError(error));
      setMessageIsError(true);
    } finally {
      setSaving(false);
    }
  }

  return (
    <PageTransition>
      <div className="space-y-6">
        <div>
          <h2 className="text-2xl font-semibold">Templates</h2>
          <p className="muted-text">Manage invoice branding templates used by compose/invoice screens.</p>
        </div>

        <Card>
          <CardHeader>
            <CardTitle>Create template</CardTitle>
          </CardHeader>
          <CardContent>
            <form className="space-y-6" onSubmit={onSubmit}>

              {/* Basic info */}
              <div className="space-y-3">
                <h3 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">Basic info</h3>
                <div className="grid gap-3 md:grid-cols-2">
                  <div className="space-y-1">
                    <label className="text-sm font-medium">Template name <span className="text-rose-500">*</span></label>
                    <Input
                      required
                      placeholder="e.g. Default, Corporate, Minimal"
                      value={form.name}
                      onChange={(e) => setForm((s) => ({ ...s, name: e.target.value }))}
                    />
                  </div>
                  <div className="flex items-end">
                    <label className="flex cursor-pointer items-center gap-2 rounded-xl border border-input px-3 py-2.5 text-sm w-full">
                      <input
                        type="checkbox"
                        checked={form.is_default}
                        onChange={(e) => setForm((s) => ({ ...s, is_default: e.target.checked }))}
                      />
                      <span>Set as default template</span>
                    </label>
                  </div>
                </div>
              </div>

              {/* Branding colours */}
              <div className="space-y-3">
                <h3 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">Branding colours</h3>
                <div className="grid gap-5 md:grid-cols-2">
                  <ColourPicker
                    label="Primary colour"
                    description="Used for headings and key invoice elements"
                    value={form.primary_colour}
                    onChange={(v) => setForm((s) => ({ ...s, primary_colour: v }))}
                  />
                  <ColourPicker
                    label="Secondary colour"
                    description="Used for accents, borders, and sub-headings"
                    value={form.secondary_colour}
                    onChange={(v) => setForm((s) => ({ ...s, secondary_colour: v }))}
                  />
                </div>
              </div>

              {/* Invoice content */}
              <div className="space-y-3">
                <h3 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">Invoice content</h3>
                <div className="space-y-1">
                  <label className="text-sm font-medium">Footer text</label>
                  <p className="text-xs text-muted-foreground">Appears at the bottom of every invoice (e.g. thank-you note)</p>
                  <Textarea
                    rows={2}
                    placeholder="e.g. Thank you for your business!"
                    value={form.footer_text}
                    onChange={(e) => setForm((s) => ({ ...s, footer_text: e.target.value }))}
                  />
                </div>
                <div className="space-y-1">
                  <label className="text-sm font-medium">Payment terms</label>
                  <p className="text-xs text-muted-foreground">Standard payment conditions shown on invoices</p>
                  <Textarea
                    rows={2}
                    placeholder="e.g. Payment due within 30 days of invoice date."
                    value={form.payment_terms_text}
                    onChange={(e) => setForm((s) => ({ ...s, payment_terms_text: e.target.value }))}
                  />
                </div>
                <div className="space-y-1">
                  <label className="text-sm font-medium">Bank details</label>
                  <p className="text-xs text-muted-foreground">Banking information printed for payment reference</p>
                  <Textarea
                    rows={3}
                    placeholder="e.g. BSB: 000-000  Account: 12345678  Bank: Example Bank"
                    value={form.bank_details}
                    onChange={(e) => setForm((s) => ({ ...s, bank_details: e.target.value }))}
                  />
                </div>
              </div>

              <div className="flex items-center gap-3">
                <Button type="submit" disabled={saving || !form.name}>
                  {saving ? "Saving…" : "Save template"}
                </Button>
                {message ? (
                  <p className={`text-sm ${messageIsError ? "text-rose-600" : "text-green-600"}`}>
                    {message}
                  </p>
                ) : null}
              </div>
            </form>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Template library</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {loading ? (
              <p className="muted-text">Loading templates…</p>
            ) : templates.length === 0 ? (
              <p className="muted-text">No templates yet. Create one above.</p>
            ) : (
              templates.map((template) => (
                <div key={template.template_id} className="rounded-xl border border-border p-4 space-y-2">
                  <div className="flex items-center justify-between">
                    <p className="font-medium">{template.name}</p>
                    {template.is_default ? (
                      <span className="rounded-full bg-lavender px-2 py-0.5 text-xs">default</span>
                    ) : null}
                  </div>
                  <div className="flex items-center gap-4 text-sm text-muted-foreground">
                    <span className="flex items-center gap-1.5">
                      <span
                        className="inline-block h-4 w-4 rounded-full border border-border"
                        style={{ background: template.primary_colour }}
                      />
                      Primary
                    </span>
                    <span className="flex items-center gap-1.5">
                      <span
                        className="inline-block h-4 w-4 rounded-full border border-border"
                        style={{ background: template.secondary_colour }}
                      />
                      Secondary
                    </span>
                  </div>
                  {template.footer_text ? (
                    <p className="text-xs text-muted-foreground truncate">Footer: {template.footer_text}</p>
                  ) : null}
                </div>
              ))
            )}
          </CardContent>
        </Card>
      </div>
    </PageTransition>
  );
}
