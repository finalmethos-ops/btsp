"use client";

import { AdminShell } from "@/components/AdminShell";
import { NotificationAdministrationPanel } from "@/components/NotificationAdministrationPanel";
import { ProtectedRoute } from "@/components/ProtectedRoute";

export default function AdminNotificationsPage() {
  return (
    <ProtectedRoute requiredPermission="notifications.manage">
      <AdminShell>
        <NotificationAdministrationPanel />
      </AdminShell>
    </ProtectedRoute>
  );
}
