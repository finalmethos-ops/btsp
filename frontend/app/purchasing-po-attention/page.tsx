import { ProtectedRoute } from "@/components/ProtectedRoute";
import { PurchasingPOMonitorWorkspace } from "@/components/PurchasingPOMonitorWorkspace";

export default function PurchasingPOAttentionPage() {
  return (
    <ProtectedRoute requiredPermission="purchase_orders.handoff">
      <PurchasingPOMonitorWorkspace initialQueue="attention" />
    </ProtectedRoute>
  );
}
