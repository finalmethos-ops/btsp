"use client";

import { AdminShell } from "@/components/AdminShell";
import { AuditReportingPanel } from "@/components/AuditReportingPanel";
import { ProtectedRoute } from "@/components/ProtectedRoute";

export default function AdminAuditPage() {
  return (
    <ProtectedRoute requiredPermission="snapshots.read">
      <AdminShell>
        <AuditReportingPanel />
      </AdminShell>
    </ProtectedRoute>
  );
}
