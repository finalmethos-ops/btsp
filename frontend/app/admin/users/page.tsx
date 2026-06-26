'use client';

import { AdminShell } from '@/components/AdminShell';
import { ProtectedRoute } from '@/components/ProtectedRoute';
import { UserManagementPanel } from '@/components/UserManagementPanel';

export default function AdminUsersPage() {
  return (
    <ProtectedRoute requiredPermission="system.admin">
      <AdminShell>
        <UserManagementPanel />
      </AdminShell>
    </ProtectedRoute>
  );
}
