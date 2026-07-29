import { ProtectedRoute } from "@/components/ProtectedRoute";
import { StoreManagementWorkspace } from "@/components/StoreManagementWorkspace";

export default function StoreManagementPage() {
  return (
    <ProtectedRoute requiredPermission="stores.read">
      <StoreManagementWorkspace />
    </ProtectedRoute>
  );
}
