import { AdminShell } from "@/components/AdminShell";
import { ProtectedRoute } from "@/components/ProtectedRoute";
import { UserManagementPanel } from "@/components/UserManagementPanel";
import { VendorManagementPanel } from "@/components/VendorManagementPanel";
export default function VendorManagementPage() {
  return (
    <ProtectedRoute requiredPermission="system.admin">
      <AdminShell>
        <VendorManagementPanel />
        <UserManagementPanel audience="vendor" />
      </AdminShell>
    </ProtectedRoute>
  );
}
