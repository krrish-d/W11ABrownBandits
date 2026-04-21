"use client";

import { useEffect, useState } from "react";
import { fetchAuditLogs, getApiError } from "@/lib/api";
import type { AuditLog } from "@/lib/types";
import { PageTransition } from "@/components/page-transition";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

export default function AuditPage() {
  const [logs, setLogs] = useState<AuditLog[]>([]);
  const [entityType, setEntityType] = useState("");
  const [action, setAction] = useState("");
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(true);

  async function loadLogs() {
    try {
      setLoading(true);
      setMessage("");
      const data = await fetchAuditLogs({
        entity_type: entityType || undefined,
        action: action || undefined,
        limit: 100,
      });
      setLogs(data);
    } catch (error) {
      setMessage(getApiError(error));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadLogs();
  }, []);

  return (
    <PageTransition>
      <div className="space-y-6">
        <div>
          <h2 className="text-2xl font-semibold">Audit</h2>
          <p className="muted-text">Track create/update/delete events for invoices, templates and recurring rules.</p>
        </div>

        <Card>
          <CardHeader>
            <CardTitle>Filter audit logs</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="grid gap-3 md:grid-cols-3">
              <Input placeholder="Entity type (invoice, template...)" value={entityType} onChange={(e) => setEntityType(e.target.value)} />
              <Input placeholder="Action (create, update, delete)" value={action} onChange={(e) => setAction(e.target.value)} />
              <Button type="button" onClick={loadLogs}>
                Apply filters
              </Button>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Audit log entries</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {loading ? (
              <p className="muted-text">Loading audit logs...</p>
            ) : logs.length === 0 ? (
              <p className="muted-text">No audit logs returned.</p>
            ) : (
              logs.map((log) => (
                <div key={log.audit_id} className="rounded-xl border border-border p-3">
                  <p className="font-medium">
                    {log.entity_type} - {log.action}
                  </p>
                  <p className="muted-text">Entity: {log.entity_id}</p>
                  <p className="muted-text">By: {log.changed_by || "system"}</p>
                  <p className="muted-text">{new Date(log.timestamp).toLocaleString()}</p>
                </div>
              ))
            )}
            {message ? <p className="muted-text text-rose-700">{message}</p> : null}
          </CardContent>
        </Card>
      </div>
    </PageTransition>
  );
}
