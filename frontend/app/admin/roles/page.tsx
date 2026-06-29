"use client";

import { AdminShell } from "@/components/AdminShell";
import { ProtectedRoute } from "@/components/ProtectedRoute";
import { RoleManagementPanel } from "@/components/RoleManagementPanel";

export default function AdminRolesPage() {
  return (
    <ProtectedRoute requiredPermission="roles.manage">
      <AdminShell>
        <RoleManagementPanel />
      </AdminShell>
    </ProtectedRoute>
  );
}
