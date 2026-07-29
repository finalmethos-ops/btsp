import { OrderRequestLifecycleWorkspace } from "@/components/OrderRequestLifecycleWorkspace";
import { ProtectedRoute } from "@/components/ProtectedRoute";

export default function VendorOrderRequestsPage() {
  return (
    <ProtectedRoute requiredPermission="vendor.portal">
      <OrderRequestLifecycleWorkspace mode="vendor" />
    </ProtectedRoute>
  );
}
