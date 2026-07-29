import { AdminShell } from "@/components/AdminShell";
import { EntityRegionManagementPanel } from "@/components/EntityRegionManagementPanel";
import { ProtectedRoute } from "@/components/ProtectedRoute";
import { UserManagementPanel } from "@/components/UserManagementPanel";
export default function BuddysUsersPage() {
  return (
    <ProtectedRoute requiredPermission="system.admin">
      <AdminShell>
        <UserManagementPanel audience="buddys" />
        <EntityRegionManagementPanel />
      </AdminShell>
    </ProtectedRoute>
  );
}
