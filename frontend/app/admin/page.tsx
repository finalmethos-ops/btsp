"use client";

import Link from "next/link";
import { AdminShell } from "@/components/AdminShell";
import { ProtectedRoute } from "@/components/ProtectedRoute";
import { useAuth } from "@/lib/auth";

const adminActions = [
  {
    title: "Vendor management",
    description:
      "Manage vendor companies, representatives, access, and credentials.",
    href: "/admin/vendor-management",
    permission: "system.admin",
  },
  {
    title: "Buddy’s users",
    description:
      "Manage internal users, stores, entities, regions, and assignments.",
    href: "/admin/buddys-users",
    permission: "system.admin",
  },
  {
    title: "Roles & permissions",
    description: "Review role definitions and permission grants.",
    href: "/admin/roles",
    permission: "roles.manage",
  },
  {
    title: "Workflows",
    description: "Administer workflow definitions and operational transitions.",
    href: "/admin/workflows",
    permission: "workflows.manage",
  },
  {
    title: "Notifications",
    description: "Manage notification templates, delivery, and preferences.",
    href: "/admin/notifications",
    permission: "notifications.manage",
  },
  {
    title: "System health",
    description:
      "Check service health, jobs, integrations, and operational alerts.",
    href: "/admin/system-health",
    permission: "system.health.read",
  },
  {
    title: "Configuration",
    description:
      "Review settings and approve controlled configuration changes.",
    href: "/admin/configuration",
    permission: "configuration.manage",
  },
  {
    title: "Audit reporting",
    description: "Review audit evidence and administrative activity.",
    href: "/admin/audit",
    permission: "snapshots.read",
  },
] as const;

export default function AdminHomePage() {
  const { user } = useAuth();
  const actions = adminActions.filter((action) =>
    user?.permissions.includes(action.permission),
  );

  return (
    <ProtectedRoute>
      <AdminShell contentClassName="admin-overview-surface">
        <div className="admin-overview">
          <div className="admin-overview-heading">
            <div>
              <span className="brand-badge">Administration workspace</span>
              <h2>What would you like to manage?</h2>
              <p>
                Choose an administrative function below. Only workspaces
                available to your role are shown.
              </p>
            </div>
            <Link className="brand-button" href="/">
              Command center
            </Link>
          </div>
          {actions.length ? (
            <div className="admin-overview-grid">
              {actions.map((action) => (
                <Link
                  className="admin-overview-card"
                  href={action.href}
                  key={action.href}
                >
                  <span
                    className="admin-overview-card-arrow"
                    aria-hidden="true"
                  >
                    →
                  </span>
                  <h3>{action.title}</h3>
                  <p>{action.description}</p>
                </Link>
              ))}
            </div>
          ) : (
            <div className="admin-overview-empty">
              Your account does not have an administrative workspace assigned.
            </div>
          )}
        </div>
      </AdminShell>
    </ProtectedRoute>
  );
}
