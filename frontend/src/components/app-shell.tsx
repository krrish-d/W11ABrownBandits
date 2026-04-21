"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { BarChart3, FileText, Home, LogOut, PencilLine, ReceiptText, Users, Wand2, ShieldCheck, Repeat, Palette, ClipboardList } from "lucide-react";
import { cn } from "@/lib/utils";
import { clearStoredToken, fetchMe, getStoredToken } from "@/lib/api";
import { ThemeSwitcher } from "@/components/theme-switcher";

const links = [
  { href: "/", label: "Dashboard", icon: Home },
  { href: "/invoices", label: "Invoices", icon: FileText },
  { href: "/compose", label: "Compose", icon: PencilLine },
  { href: "/clients", label: "Clients", icon: Users },
  { href: "/analytics", label: "Analytics", icon: BarChart3 },
  { href: "/payments", label: "Payments", icon: ReceiptText },
  { href: "/transform", label: "Transform", icon: Wand2 },
  { href: "/validate", label: "Validate", icon: ShieldCheck },
  { href: "/templates", label: "Templates", icon: Palette },
  { href: "/recurring", label: "Recurring", icon: Repeat },
  { href: "/audit", label: "Audit", icon: ClipboardList },
];

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname() || "/";
  const [authChecked, setAuthChecked] = useState(false);
  const authed = !!getStoredToken();
  const isPublicRoute = pathname === "/login";

  // Restore saved theme on mount to avoid flash
  useEffect(() => {
    const saved = localStorage.getItem("invoiceflow_theme") ?? "lavender";
    if (saved && saved !== "lavender") {
      document.documentElement.setAttribute("data-theme", saved);
    }
  }, []);

  useEffect(() => {
    let active = true;

    async function ensureSession() {
      setAuthChecked(false);

      if (isPublicRoute) {
        if (active) setAuthChecked(true);
        return;
      }

      const token = getStoredToken();
      if (!token) {
        window.location.href = "/login";
        return;
      }

      try {
        await fetchMe();
        if (active) setAuthChecked(true);
      } catch {
        clearStoredToken();
        window.location.href = "/login";
      }
    }

    ensureSession();
    return () => {
      active = false;
    };
  }, [isPublicRoute, pathname]);

  if (!isPublicRoute && !authChecked) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background">
        <p className="text-sm text-muted-foreground">Checking session...</p>
      </div>
    );
  }

  return (
    <div className="flex h-screen flex-col overflow-hidden bg-background">
      <header className="border-b border-border bg-card/80 backdrop-blur md:hidden">
        <div className="w-full px-4 py-3 sm:px-6">
          <div className="mb-3 flex items-center justify-between">
            <div>
              <h1 className="text-base font-semibold tracking-tight">InvoiceFlow</h1>
              <p className="text-xs text-muted-foreground">Clean invoicing with modern automation</p>
            </div>
            {authed ? (
              <button
                type="button"
                onClick={() => {
                  clearStoredToken();
                  window.location.href = "/login";
                }}
                className="rounded-xl border border-border px-3 py-1.5 text-xs text-muted-foreground transition hover:bg-cream hover:text-foreground"
              >
                Logout
              </button>
            ) : (
              <Link
                href="/login"
                className="rounded-xl border border-border px-3 py-1.5 text-xs text-muted-foreground transition hover:bg-cream hover:text-foreground"
              >
                Login
              </Link>
            )}
          </div>
          <nav className="-mx-1 flex gap-2 overflow-x-auto px-1 pb-1">
            {links.map((link) => {
              const Icon = link.icon;
              const active = pathname === link.href || pathname.startsWith(link.href + "/");
              return (
                <Link
                  key={link.href}
                  href={link.href}
                  className={cn(
                    "inline-flex shrink-0 items-center gap-1.5 rounded-xl px-3 py-1.5 text-xs transition-colors",
                    active ? "bg-lavender text-foreground" : "text-muted-foreground hover:bg-cream hover:text-foreground"
                  )}
                >
                  <Icon className="h-3.5 w-3.5" />
                  {link.label}
                </Link>
              );
            })}
          </nav>
        </div>
      </header>
      <div className="flex flex-1 gap-0 overflow-hidden">
        <aside className="hidden w-60 shrink-0 border-r border-border bg-card p-4 md:flex md:flex-col md:overflow-y-auto">
          <h1 className="mb-3 px-2 text-xl font-semibold tracking-tight">InvoiceFlow</h1>
          <p className="mb-6 px-2 text-xs text-muted-foreground">Clean invoicing with modern automation</p>
          <nav className="space-y-2">
            {links.map((link) => {
              const Icon = link.icon;
              const active = pathname === link.href || pathname.startsWith(link.href + "/");
              return (
                <Link
                  key={link.href}
                  href={link.href}
                  className={cn(
                    "flex items-center gap-2 rounded-xl px-3 py-2 text-sm transition-colors",
                    active ? "bg-lavender text-foreground" : "text-muted-foreground hover:bg-cream hover:text-foreground"
                  )}
                >
                  <Icon className="h-4 w-4" />
                  {link.label}
                </Link>
              );
            })}
          </nav>
          <ThemeSwitcher />
          <div className="mt-4 border-t border-border pt-4">
            {authed ? (
              <button
                type="button"
                onClick={() => {
                  clearStoredToken();
                  window.location.href = "/login";
                }}
                className="flex w-full items-center gap-2 rounded-xl px-3 py-2 text-sm text-muted-foreground transition hover:bg-cream hover:text-foreground"
              >
                <LogOut className="h-4 w-4" />
                Logout
              </button>
            ) : (
              <Link
                href="/login"
                className="flex w-full items-center gap-2 rounded-xl px-3 py-2 text-sm text-muted-foreground transition hover:bg-cream hover:text-foreground"
              >
                <LogOut className="h-4 w-4" />
                Login
              </Link>
            )}
          </div>
        </aside>
        <main className="min-w-0 flex-1 overflow-y-auto p-6 md:p-8">{children}</main>
      </div>
    </div>
  );
}

