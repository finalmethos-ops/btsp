"use client";

import { AdminShell } from "@/components/AdminShell";
import { ProtectedRoute } from "@/components/ProtectedRoute";
import { SystemHealthPanel } from "@/components/SystemHealthPanel";

export default function AdminSystemHealthPage() {
  return (
    <ProtectedRoute requiredPermission="system.health.read">
      <AdminShell>
        <SystemHealthPanel />
      </AdminShell>
    </ProtectedRoute>
  );
}
