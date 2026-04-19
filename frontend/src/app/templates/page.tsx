"use client";

import { useEffect, useState } from "react";
import { createTemplate, fetchTemplates, getApiError } from "@/lib/api";
import type { Template } from "@/lib/types";
import { PageTransition } from "@/components/page-transition";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";

export default function TemplatesPage() {
  const [templates, setTemplates] = useState<Template[]>([]);
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(true);
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
      setMessage("Template saved.");
      await loadTemplates();
    } catch (error) {
      setMessage(getApiError(error));
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
            <form className="space-y-3" onSubmit={onSubmit}>
              <div className="grid gap-3 md:grid-cols-2">
                <Input placeholder="Template name" value={form.name} onChange={(e) => setForm((s) => ({ ...s, name: e.target.value }))} />
                <label className="flex items-center gap-2 rounded-xl border border-input px-3 py-2 text-sm">
                  <input
                    type="checkbox"
                    checked={form.is_default}
                    onChange={(e) => setForm((s) => ({ ...s, is_default: e.target.checked }))}
                  />
                  Set as default
                </label>
                <Input
                  placeholder="Primary colour (#hex)"
                  value={form.primary_colour}
                  onChange={(e) => setForm((s) => ({ ...s, primary_colour: e.target.value }))}
                />
                <Input
                  placeholder="Secondary colour (#hex)"
                  value={form.secondary_colour}
                  onChange={(e) => setForm((s) => ({ ...s, secondary_colour: e.target.value }))}
                />
              </div>
              <Textarea
                rows={2}
                placeholder="Footer text"
                value={form.footer_text}
                onChange={(e) => setForm((s) => ({ ...s, footer_text: e.target.value }))}
              />
              <Textarea
                rows={2}
                placeholder="Payment terms text"
                value={form.payment_terms_text}
                onChange={(e) => setForm((s) => ({ ...s, payment_terms_text: e.target.value }))}
              />
              <Textarea
                rows={3}
                placeholder="Bank details"
                value={form.bank_details}
                onChange={(e) => setForm((s) => ({ ...s, bank_details: e.target.value }))}
              />
              <Button type="submit">Save template</Button>
            </form>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Template library</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {loading ? (
              <p className="muted-text">Loading templates...</p>
            ) : templates.length === 0 ? (
              <p className="muted-text">No templates yet.</p>
            ) : (
              templates.map((template) => (
                <div key={template.template_id} className="rounded-xl border border-border p-3">
                  <div className="flex items-center justify-between">
                    <p className="font-medium">{template.name}</p>
                    {template.is_default ? <span className="rounded-full bg-lavender px-2 py-0.5 text-xs">default</span> : null}
                  </div>
                  <p className="muted-text">
                    {template.primary_colour} / {template.secondary_colour}
                  </p>
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
