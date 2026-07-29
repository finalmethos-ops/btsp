import { ProtectedRoute } from "@/components/ProtectedRoute";
import { VendorActivePOWorkspace } from "@/components/VendorActivePOWorkspace";

export default function VendorActivePOPage() {
  return (
    <ProtectedRoute requiredPermission="vendor.portal">
      <VendorActivePOWorkspace queue="active" />
    </ProtectedRoute>
  );
}
