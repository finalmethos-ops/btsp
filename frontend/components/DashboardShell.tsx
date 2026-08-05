"use client";

import Image from "next/image";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { MessageNotificationLink } from "@/components/MessageNotificationLink";
import { ExecutiveSpendCommandCenter } from "@/components/ExecutiveSpendCommandCenter";
import { PlatformSidebar } from "@/components/PlatformSidebar";
import { AvailableWorkflow, getAvailableWorkflows } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import {
  listPurchasingLifecyclePOs,
  listVendorPOs,
} from "@/lib/order-lifecycle-api";
import { rolePriority, roleWorkspaces } from "@/lib/role-workspaces";

type WorkspaceModule = {
  href?: string;
  title: string;
  description: string;
  badge?: string;
  attentionQueue?: "vendor" | "purchasing";
};

export function DashboardShell() {
  const { user, signOut } = useAuth();
  const pathname = usePathname();
  const router = useRouter();
  const [workflows, setWorkflows] = useState<AvailableWorkflow[]>([]);
  const [attentionCounts, setAttentionCounts] = useState<
    Partial<Record<"vendor" | "purchasing", number>>
  >({});

  useEffect(() => {
    async function loadWorkflows() {
      setWorkflows(await getAvailableWorkflows());
    }

    if (user) {
      void loadWorkflows();
    }
  }, [user]);

  useEffect(() => {
    if (!user) return;
    const queues = new Set(
      rolePriority
        .map((role) =>
          user.roles.includes(role) ? roleWorkspaces[role] : undefined,
        )
        .flatMap((workspace) => workspace?.modules ?? [])
        .map((module) => module.attentionQueue)
        .filter(
          (queue): queue is "vendor" | "purchasing" => queue !== undefined,
        ),
    );
    if (!queues.size) return;
    let active = true;
    async function refreshAttentionCounts() {
      try {
        const entries = await Promise.all(
          [...queues].map(async (queue) => {
            const orders =
              queue === "vendor"
                ? await listVendorPOs("attention")
                : await listPurchasingLifecyclePOs("attention");
            return [queue, orders.length] as const;
          }),
        );
        if (active) setAttentionCounts(Object.fromEntries(entries));
      } catch {
        // Queue polling must not interrupt the command center.
      }
    }
    void refreshAttentionCounts();
    const timer = window.setInterval(
      () => void refreshAttentionCounts(),
      30_000,
    );
    const onVisibility = () => {
      if (document.visibilityState === "visible") void refreshAttentionCounts();
    };
    document.addEventListener("visibilitychange", onVisibility);
    return () => {
      active = false;
      window.clearInterval(timer);
      document.removeEventListener("visibilitychange", onVisibility);
    };
  }, [user]);

  if (!user) {
    return null;
  }

  const primaryRole = rolePriority.find((role) => user.roles.includes(role));
  const roleWorkspace = primaryRole ? roleWorkspaces[primaryRole] : undefined;
  const isEventAdmin = user.permissions.includes("events.manage");
  // Event workspaces are deliberately isolated from the standard portal.
  // Attendees enter through /event-login so event modules cannot clutter or
  // leak into their purchasing command center.
  const modules: WorkspaceModule[] = roleWorkspace
    ? roleWorkspace.modules.filter(
        (module) => isEventAdmin || module.badge !== "Event scoped",
      )
    : workflows.map((workflow) => ({
        href: workflow.route,
        title: workflow.name,
        description: `Open the ${workflow.code} workflow, approvals, and purchasing actions.`,
      }));

  if (isEventAdmin && user.permissions.includes("events.read")) {
    modules.push({
      href: "/events",
      title: "My Events",
      description: "Open live buying events assigned to your entity.",
      badge: "Event scoped",
    });
  }

  if (
    !roleWorkspace &&
    user.permissions.some((permission) =>
      [
        "orders.bpp.manage",
        "orders.independent.manage",
        "system.admin",
      ].includes(permission),
    )
  ) {
    modules.unshift({
      href: "/purchase-orders",
      title: "Purchase Orders",
      description:
        "Generate, export, split, consolidate, and track vendor handoffs.",
    });
  }
  if (!roleWorkspace && user.permissions.includes("vendor.integrations.read")) {
    modules.push({
      href: "/vendor-connectors",
      title: "Vendor Connectors",
      description:
        "Monitor partner endpoints, imports, retries, leases, and dead letters.",
    });
  }
  if (!roleWorkspace && user.permissions.includes("receiving.read")) {
    modules.push({
      href: "/receiving",
      title: "Receiving",
      description:
        "Post physical receipts and resolve quantity or shipment variances.",
    });
  }
  if (!roleWorkspace && user.permissions.includes("invoices.read")) {
    modules.push({
      href: "/invoices",
      title: "Invoice Intelligence",
      description:
        "Review vendor invoices, line matching, and reconciliation exceptions.",
    });
  }
  if (!roleWorkspace && user.permissions.includes("analytics.read")) {
    modules.push({
      href: "/analytics",
      title: "Analytics & Insights",
      description:
        "Explore spend, vendor, approval, inventory, and operational performance.",
    });
  }
  if (
    !roleWorkspace &&
    user.permissions.some((permission) =>
      [
        "system.admin",
        "roles.manage",
        "configuration.manage",
        "system.health.read",
      ].includes(permission),
    )
  ) {
    modules.push({
      href: "/admin",
      title: "Administration",
      description:
        "Govern users, roles, workflows, notifications, configuration, and audit.",
    });
  }
  return (
    <div className="brand-shell">
      <header className="brand-ribbon">
        <Link className="brand-lockup" href="/">
          <Image
            alt="Buddy's Home Furnishings"
            className="command-center-logo"
            height={58}
            priority
            src="/brand/buddys-logo-compact.png"
            width={145}
          />
        </Link>
        <div className="brand-ribbon-actions flex items-center gap-4">
          {user.vendor_accounts.length > 1 ? (
            <Link className="brand-button" href="/vendor-select">
              Switch vendor
            </Link>
          ) : null}
          <MessageNotificationLink />
          <div className="brand-user">
            <strong>{user.display_name}</strong>
            {user.roles.join(" · ") || "No role assigned"}
          </div>
          <button
            aria-label="Sign out"
            className="brand-button brand-button-signout"
            onClick={() => {
              signOut();
              router.replace("/");
            }}
            title="Sign out"
            type="button"
          >
            <svg
              aria-hidden="true"
              className="nav-action-icon"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d="M10 17l5-5-5-5" />
              <path d="M15 12H3" />
              <path d="M21 3v18" />
            </svg>
            <span className="nav-action-label">Sign out</span>
          </button>
        </div>
      </header>

      <div className="dashboard-layout">
        {primaryRole === "ADMIN" || primaryRole === "SYSTEM_ADMIN" ? (
          <PlatformSidebar />
        ) : (
          <aside className="brand-sidebar">
            <div className="sidebar-branding">
              <Image
                alt="Purchasing Intelligence branding"
                fill
                sizes="245px"
                src="/brand/purchasing-intelligence-short.png"
              />
            </div>
            <nav className="brand-nav" aria-label="Workspace navigation">
              <Link className={pathname === "/" ? "is-selected" : ""} href="/">
                Command Center
              </Link>
              {modules
                .filter(
                  (module): module is WorkspaceModule & { href: string } =>
                    Boolean(module.href),
                )
                .map((module) => (
                  <Link
                    className={pathname === module.href ? "is-selected" : ""}
                    href={module.href}
                    key={`${module.href}-${module.title}`}
                  >
                    {module.title}
                  </Link>
                ))}
            </nav>
          </aside>
        )}

        <main className="workspace-main">
          <section className="workspace-hero">
            <span className="brand-badge">
              {roleWorkspace?.roleLabel ?? "Live purchasing workspace"}
            </span>
            <h1>
              {roleWorkspace?.headline ??
                "Make every purchasing decision count."}
            </h1>
            <p>
              Welcome, {user.display_name}.{" "}
              {roleWorkspace?.summary ??
                "Your command center brings authorized workflows, operations, and intelligence into one focused experience."}
            </p>
            {primaryRole === "VENDOR" && user.vendor_code ? (
              <p className="brand-eyebrow mt-4">
                Vendor identity: {user.vendor_code}
              </p>
            ) : null}
          </section>

          {user.roles.includes("EXECUTIVE") ? (
            <ExecutiveSpendCommandCenter />
          ) : null}

          <section className="module-grid">
            {modules.map((module) => {
              const attentionCount = module.attentionQueue
                ? (attentionCounts[module.attentionQueue] ?? 0)
                : 0;
              const content = (
                <>
                  {attentionCount > 0 ? (
                    <span
                      aria-label={`${attentionCount} purchase orders need attention`}
                      className="module-attention-count"
                    >
                      {attentionCount > 99 ? "99+" : attentionCount}
                    </span>
                  ) : null}
                  <h3>{module.title}</h3>
                  <p>{module.description}</p>
                  <span>
                    {module.href
                      ? "Open workspace →"
                      : (module.badge ?? "Role scoped")}
                  </span>
                </>
              );
              return module.href ? (
                <Link
                  className="module-card"
                  href={module.href}
                  key={`${module.href}-${module.title}`}
                >
                  {content}
                </Link>
              ) : (
                <div className="module-card" key={module.title}>
                  {content}
                </div>
              );
            })}
            {modules.length === 0 ? (
              <div className="module-card">
                <h3>No workspaces assigned</h3>
                <p>
                  Contact an administrator to review your role and module
                  access.
                </p>
              </div>
            ) : null}
          </section>
        </main>
      </div>
    </div>
  );
}
