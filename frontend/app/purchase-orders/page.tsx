import { ProtectedRoute } from "@/components/ProtectedRoute";
import { PurchaseOrderWorkspace } from "@/components/PurchaseOrderWorkspace";

export default function PurchaseOrdersPage() {
  return (
    <ProtectedRoute>
      <PurchaseOrderWorkspace />
    </ProtectedRoute>
  );
}
