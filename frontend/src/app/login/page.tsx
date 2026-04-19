"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { fetchMe, getApiError, login, signup } from "@/lib/api";
import { PageTransition } from "@/components/page-transition";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";

export default function LoginPage() {
  const [mode, setMode] = useState<"login" | "signup">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);
  const router = useRouter();

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    try {
      setLoading(true);
      setMessage("");
      if (mode === "login") {
        await login(email, password);
      } else {
        await signup({ email, password, full_name: name || undefined });
      }
      await fetchMe();
      router.push("/");
    } catch (error) {
      setMessage(getApiError(error));
    } finally {
      setLoading(false);
    }
  }

  return (
    <PageTransition>
      <div className="mx-auto max-w-md pt-8">
        <Card>
          <CardHeader>
            <CardTitle>{mode === "login" ? "Login" : "Create account"}</CardTitle>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-4">
              {mode === "signup" ? (
                <div>
                  <label className="muted-text">Full name</label>
                  <Input value={name} onChange={(e) => setName(e.target.value)} placeholder="Jane Doe" />
                </div>
              ) : null}
              <div>
                <label className="muted-text">Email</label>
                <Input value={email} onChange={(e) => setEmail(e.target.value)} type="email" placeholder="you@example.com" />
              </div>
              <div>
                <label className="muted-text">Password</label>
                <Input value={password} onChange={(e) => setPassword(e.target.value)} type="password" placeholder="••••••••" />
              </div>
              <Button disabled={loading} type="submit">
                {loading ? "Please wait..." : mode === "login" ? "Login" : "Sign up"}
              </Button>
              {message ? <p className="muted-text text-rose-700">{message}</p> : null}
            </form>
            <button
              type="button"
              className="mt-4 text-sm text-muted-foreground underline"
              onClick={() => setMode((m) => (m === "login" ? "signup" : "login"))}
            >
              {mode === "login" ? "Need an account? Sign up" : "Already have an account? Login"}
            </button>
          </CardContent>
        </Card>
      </div>
    </PageTransition>
  );
}
