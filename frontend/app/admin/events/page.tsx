"use client";

import { AdminShell } from "@/components/AdminShell";
import { EventAdministrationPanel } from "@/components/EventAdministrationPanel";
import { ProtectedRoute } from "@/components/ProtectedRoute";

export default function AdminEventsPage() {
  return (
    <ProtectedRoute requiredPermission="events.manage">
      <AdminShell>
        <EventAdministrationPanel />
      </AdminShell>
    </ProtectedRoute>
  );
}
