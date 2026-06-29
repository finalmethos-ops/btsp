"use client";

import { ReactNode } from "react";
import Link from "next/link";
import { useAuth } from "@/lib/auth";
import { visibleAdminNavigation } from "@/lib/permissions";

export function AdminShell({ children }: { children: ReactNode }) {
  const { user } = useAuth();
  const navigation = visibleAdminNavigation(user);

  return (
    <main className="mx-auto max-w-6xl p-8">
      <header className="mb-8">
        <Link className="text-sm text-slate-600" href="/">
          ← Back to dashboard
        </Link>
        <h1 className="mt-4 text-3xl font-bold">Administration</h1>
        <p className="mt-2 text-slate-600">
          Manage BTSP users, store data, configuration, and audit records.
        </p>
      </header>

      <div className="grid gap-6 md:grid-cols-[220px_1fr]">
        <nav className="rounded-lg bg-white p-4 shadow">
          <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-slate-500">
            Admin
          </h2>
          <div className="flex flex-col gap-2">
            {navigation.map((item) => (
              <a
                className="rounded px-3 py-2 text-sm hover:bg-slate-100"
                href={item.href}
                key={item.href}
              >
                {item.label}
              </a>
            ))}
          </div>
        </nav>
        <section className="rounded-lg bg-white p-6 shadow">{children}</section>
      </div>
    </main>
  );
}
