"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { BarChart3, FileText, Home, LogOut, PencilLine, ReceiptText, Users } from "lucide-react";
import { cn } from "@/lib/utils";
import { clearStoredToken, getStoredToken } from "@/lib/api";

const links = [
  { href: "/", label: "Dashboard", icon: Home },
  { href: "/invoices", label: "Invoices", icon: FileText },
  { href: "/compose", label: "Compose", icon: PencilLine },
  { href: "/clients", label: "Clients", icon: Users },
  { href: "/analytics", label: "Analytics", icon: BarChart3 },
  { href: "/payments", label: "Payments", icon: ReceiptText },
];

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname() || "/";
  const authed = !!getStoredToken();

  return (
    <div className="min-h-screen bg-background">
      <header className="border-b border-border bg-card/80 backdrop-blur md:hidden">
        <div className="mx-auto max-w-7xl px-4 py-3 sm:px-6">
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
      <div className="mx-auto flex max-w-7xl gap-6 px-4 py-8 sm:px-6 lg:px-8">
        <aside className="hidden w-64 shrink-0 rounded-2xl border border-border bg-card p-4 shadow-soft md:block">
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
          <div className="mt-6 border-t border-border pt-4">
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
        <main className="min-w-0 flex-1">{children}</main>
      </div>
    </div>
  );
}
