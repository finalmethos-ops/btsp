import { ProtectedRoute } from "@/components/ProtectedRoute";
import { VendorActivePOWorkspace } from "@/components/VendorActivePOWorkspace";

export default function VendorPOAttentionPage() {
  return (
    <ProtectedRoute requiredPermission="vendor.portal">
      <VendorActivePOWorkspace queue="attention" />
    </ProtectedRoute>
  );
}
