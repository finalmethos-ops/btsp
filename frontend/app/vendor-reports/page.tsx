import { ProtectedRoute } from "@/components/ProtectedRoute";
import { VendorReportsWorkspace } from "@/components/VendorReportsWorkspace";

export default function VendorReportsPage() {
  return (
    <ProtectedRoute requiredPermission="vendor.portal">
      <VendorReportsWorkspace />
    </ProtectedRoute>
  );
}
