import { OrderRequestLifecycleWorkspace } from "@/components/OrderRequestLifecycleWorkspace";
import { ProtectedRoute } from "@/components/ProtectedRoute";

export default function PurchasingOrderReviewPage() {
  return (
    <ProtectedRoute requiredPermission="purchase_orders.handoff">
      <OrderRequestLifecycleWorkspace mode="purchasing" />
    </ProtectedRoute>
  );
}
