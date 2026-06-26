'use client';

import { AdminShell } from '@/components/AdminShell';
import { ProtectedRoute } from '@/components/ProtectedRoute';

export default function AdminConfigurationPage() {
  return (
    <ProtectedRoute requiredPermission="configuration.manage">
      <AdminShell>
        <h2 className="text-2xl font-bold">Configuration</h2>
        <p className="mt-4 text-slate-600">Configuration screens will be added in a future frontend administration package.</p>
      </AdminShell>
    </ProtectedRoute>
  );
}
