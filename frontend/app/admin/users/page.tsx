'use client';

import { AdminShell } from '@/components/AdminShell';
import { ProtectedRoute } from '@/components/ProtectedRoute';

export default function AdminUsersPage() {
  return (
    <ProtectedRoute requiredPermission="system.admin">
      <AdminShell>
        <h2 className="text-2xl font-bold">Users</h2>
        <p className="mt-4 text-slate-600">User management screens will be added in a future frontend administration package.</p>
      </AdminShell>
    </ProtectedRoute>
  );
}
