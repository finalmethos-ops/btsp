import { ProtectedRoute } from "@/components/ProtectedRoute";
import { VendorProfileWorkspace } from "@/components/VendorProfileWorkspace";

export default function VendorProfilePage() {
  return (
    <ProtectedRoute requiredPermission="vendor.portal">
      <VendorProfileWorkspace />
    </ProtectedRoute>
  );
}
