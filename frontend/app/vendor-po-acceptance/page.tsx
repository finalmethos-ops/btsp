import { ProtectedRoute } from "@/components/ProtectedRoute";
import { VendorPOAcceptanceWorkspace } from "@/components/VendorPOAcceptanceWorkspace";

export default function VendorPOAcceptancePage() {
  return (
    <ProtectedRoute requiredPermission="vendor.portal">
      <VendorPOAcceptanceWorkspace />
    </ProtectedRoute>
  );
}
