'use client';

import { AdminShell } from '@/components/AdminShell';
import { ProtectedRoute } from '@/components/ProtectedRoute';

export default function AdminHomePage() {
  return (
    <ProtectedRoute requiredPermission="system.admin">
      <AdminShell>
        <h2 className="text-2xl font-bold">Admin Home</h2>
        <p className="mt-4 text-slate-600">Choose an administration area from the navigation.</p>
      </AdminShell>
    </ProtectedRoute>
  );
}
