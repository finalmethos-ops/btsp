import { ProtectedRoute } from "@/components/ProtectedRoute";
import { VendorModelWorkspace } from "@/components/VendorModelWorkspace";

export default function VendorModelsPage() {
  return (
    <ProtectedRoute requiredPermission="vendor.portal">
      <VendorModelWorkspace />
    </ProtectedRoute>
  );
}
