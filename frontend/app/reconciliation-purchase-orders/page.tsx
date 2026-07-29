import { ProtectedRoute } from "@/components/ProtectedRoute";
import { ReconciliationPurchaseOrderWorkspace } from "@/components/ReconciliationPurchaseOrderWorkspace";

export default function ReconciliationPurchaseOrdersPage() {
  return (
    <ProtectedRoute requiredPermission="reconciliation.read">
      <ReconciliationPurchaseOrderWorkspace />
    </ProtectedRoute>
  );
}
