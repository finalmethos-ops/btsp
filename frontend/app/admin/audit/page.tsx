'use client';

import { AdminShell } from '@/components/AdminShell';
import { ProtectedRoute } from '@/components/ProtectedRoute';

export default function AdminAuditPage() {
  return (
    <ProtectedRoute requiredPermission="snapshots.read">
      <AdminShell>
        <h2 className="text-2xl font-bold">Audit</h2>
        <p className="mt-4 text-slate-600">Audit screens will be added later.</p>
      </AdminShell>
    </ProtectedRoute>
  );
}
