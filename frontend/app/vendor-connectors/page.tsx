import { ProtectedRoute } from "@/components/ProtectedRoute";
import { VendorConnectorWorkspace } from "@/components/VendorConnectorWorkspace";

export default function VendorConnectorsPage() {
  return (
    <ProtectedRoute requiredPermission="vendor.integrations.read">
      <VendorConnectorWorkspace />
    </ProtectedRoute>
  );
}
