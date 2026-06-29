import { ProtectedRoute } from "@/components/ProtectedRoute";
import { PurchaseRequestWorkspace } from "@/components/PurchaseRequestWorkspace";

export default function IndependentWorkflowPage() {
  return (
    <ProtectedRoute requiredPermission="workflow.ind.submit">
      <PurchaseRequestWorkspace
        title="Independent Purchasing"
        workflowCode="IND_PURCHASING"
      />
    </ProtectedRoute>
  );
}
