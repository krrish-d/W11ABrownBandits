"use client";

import { useEffect, useState } from "react";
import { fetchDashboardTopClients, fetchDashboardTrend, getApiError } from "@/lib/api";
import type { DashboardTopClients, DashboardTrendPoint } from "@/lib/types";
import { PageTransition } from "@/components/page-transition";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export default function AnalyticsPage() {
  const [trend, setTrend] = useState<DashboardTrendPoint[]>([]);
  const [topClients, setTopClients] = useState<DashboardTopClients["top_clients"]>([]);
  const [error, setError] = useState("");

  useEffect(() => {
    Promise.all([fetchDashboardTrend(12), fetchDashboardTopClients(8)])
      .then(([trendData, topClientsData]) => {
        setTrend(trendData.monthly);
        setTopClients(topClientsData.top_clients);
      })
      .catch((e) => setError(getApiError(e)));
  }, []);

  return (
    <PageTransition>
      <div className="space-y-6">
        <div>
          <h2 className="text-2xl font-semibold">Analytics</h2>
          <p className="muted-text">Trends and client performance from backend dashboard endpoints.</p>
        </div>
        {error ? <p className="muted-text text-rose-700">{error}</p> : null}

        <Card>
          <CardHeader>
            <CardTitle>Monthly trend</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {trend.length === 0 ? (
              <p className="muted-text">No trend data yet.</p>
            ) : (
              trend.map((point) => (
                <div key={point.month} className="grid grid-cols-4 gap-2 rounded-xl border border-border p-3 text-sm">
                  <p className="font-medium">{point.month}</p>
                  <p className="muted-text">Invoiced: ${point.invoiced.toFixed(2)}</p>
                  <p className="muted-text">Paid: ${point.paid.toFixed(2)}</p>
                  <p className="muted-text">Overdue: ${point.overdue.toFixed(2)}</p>
                </div>
              ))
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Top clients</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {topClients.length === 0 ? (
              <p className="muted-text">No top clients yet.</p>
            ) : (
              topClients.map((client) => (
                <div key={client.buyer_name} className="grid grid-cols-4 gap-2 rounded-xl border border-border p-3 text-sm">
                  <p className="font-medium">{client.buyer_name}</p>
                  <p className="muted-text">Invoiced: ${client.total_invoiced.toFixed(2)}</p>
                  <p className="muted-text">Paid: ${client.total_paid.toFixed(2)}</p>
                  <p className="muted-text">Outstanding: ${client.outstanding.toFixed(2)}</p>
                </div>
              ))
            )}
          </CardContent>
        </Card>
      </div>
    </PageTransition>
  );
}
