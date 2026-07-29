"use client";

import { ReactNode } from "react";
import { PlatformSidebar } from "@/components/PlatformSidebar";

export function AdminShell({
  children,
  contentClassName = "",
}: {
  children: ReactNode;
  contentClassName?: string;
}) {
  return (
    <div className="brand-shell">
      <div className="dashboard-layout">
        <PlatformSidebar />

        <main className="workspace-main">
          <section className="workspace-hero">
            <span className="brand-badge">Controlled administration</span>
            <h1>Govern the platform with confidence.</h1>
            <p>
              Manage identities, workflows, configuration, notifications,
              health, and audit evidence through the same permission-enforced
              services as every other workspace.
            </p>
          </section>
          <section className={`rounded-2xl p-6 ${contentClassName}`.trim()}>
            {children}
          </section>
        </main>
      </div>
    </div>
  );
}
