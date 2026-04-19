"use client";

import { useEffect, useState } from "react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";
import {
  fetchDashboardKpis,
  fetchDashboardTopClients,
  fetchDashboardTrend,
  getApiError,
} from "@/lib/api";
import type { DashboardKpis, DashboardTopClients, DashboardTrendPoint } from "@/lib/types";
import { PageTransition } from "@/components/page-transition";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export default function AnalyticsPage() {
  const [trend, setTrend] = useState<DashboardTrendPoint[]>([]);
  const [topClients, setTopClients] = useState<DashboardTopClients["top_clients"]>([]);
  const [kpis, setKpis] = useState<DashboardKpis | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    Promise.all([
      fetchDashboardKpis(),
      fetchDashboardTrend(12),
      fetchDashboardTopClients(8),
    ])
      .then(([kpiData, trendData, topClientsData]) => {
        setKpis(kpiData);
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
          <p className="muted-text">Revenue trends and client performance.</p>
        </div>

        {error ? <p className="muted-text text-rose-700">{error}</p> : null}

        {/* KPI cards */}
        <div className="grid gap-4 sm:grid-cols-3">
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">Total Invoiced (all time)</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-2xl font-bold">
                {kpis ? `$${kpis.total_invoiced_all_time.toFixed(2)}` : "—"}
              </p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">Paid This Month</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-2xl font-bold text-green-600">
                {kpis ? `$${kpis.paid_this_month.toFixed(2)}` : "—"}
              </p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">Overdue Amount</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-2xl font-bold text-rose-600">
                {kpis ? `$${kpis.overdue_amount.toFixed(2)}` : "—"}
              </p>
            </CardContent>
          </Card>
        </div>

        {/* Monthly trend chart */}
        <Card>
          <CardHeader>
            <CardTitle>Monthly trend — Invoiced vs Paid</CardTitle>
          </CardHeader>
          <CardContent>
            {trend.length === 0 ? (
              <p className="muted-text">No trend data yet. Create some invoices to see the chart.</p>
            ) : (
              <ResponsiveContainer width="100%" height={320}>
                <BarChart data={trend} margin={{ top: 8, right: 16, left: 0, bottom: 8 }}>
                  <CartesianGrid strokeDasharray="3 3" className="stroke-border" />
                  <XAxis dataKey="month" tick={{ fontSize: 12 }} />
                  <YAxis tick={{ fontSize: 12 }} tickFormatter={(v: number) => `$${v}`} />
                  <Tooltip
                    formatter={(value) => typeof value === "number" ? `$${value.toFixed(2)}` : value}
                    contentStyle={{ borderRadius: "0.75rem", border: "1px solid var(--border)" }}
                  />
                  <Legend />
                  <Bar dataKey="invoiced" name="Invoiced" fill="#a5b4fc" radius={[4, 4, 0, 0]} />
                  <Bar dataKey="paid" name="Paid" fill="#86efac" radius={[4, 4, 0, 0]} />
                  <Bar dataKey="overdue" name="Overdue" fill="#fca5a5" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            )}
          </CardContent>
        </Card>

        {/* Top clients table */}
        <Card>
          <CardHeader>
            <CardTitle>Top clients</CardTitle>
          </CardHeader>
          <CardContent>
            {topClients.length === 0 ? (
              <p className="muted-text">No client data yet.</p>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-border text-left text-xs font-medium uppercase text-muted-foreground">
                      <th className="pb-2 pr-4">Client</th>
                      <th className="pb-2 pr-4 text-right">Invoiced</th>
                      <th className="pb-2 pr-4 text-right">Paid</th>
                      <th className="pb-2 text-right">Outstanding</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border">
                    {topClients.map((c) => (
                      <tr key={c.buyer_name}>
                        <td className="py-2 pr-4 font-medium">{c.buyer_name}</td>
                        <td className="py-2 pr-4 text-right">${c.total_invoiced.toFixed(2)}</td>
                        <td className="py-2 pr-4 text-right text-green-600">${c.total_paid.toFixed(2)}</td>
                        <td className="py-2 text-right text-rose-600">${c.outstanding.toFixed(2)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </PageTransition>
  );
}
