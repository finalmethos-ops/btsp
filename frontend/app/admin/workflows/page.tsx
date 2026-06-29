"use client";

import { AdminShell } from "@/components/AdminShell";
import { ProtectedRoute } from "@/components/ProtectedRoute";
import { WorkflowAdministrationPanel } from "@/components/WorkflowAdministrationPanel";

export default function AdminWorkflowsPage() {
  return (
    <ProtectedRoute requiredPermission="workflows.manage">
      <AdminShell>
        <WorkflowAdministrationPanel />
      </AdminShell>
    </ProtectedRoute>
  );
}
