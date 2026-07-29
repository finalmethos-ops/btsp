import { ProtectedRoute } from "@/components/ProtectedRoute";
import { PurchasingPOMonitorWorkspace } from "@/components/PurchasingPOMonitorWorkspace";

export default function PurchasingPOMonitorPage() {
  return (
    <ProtectedRoute requiredPermission="purchase_orders.handoff">
      <PurchasingPOMonitorWorkspace />
    </ProtectedRoute>
  );
}
