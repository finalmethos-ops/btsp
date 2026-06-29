import { ProtectedRoute } from "@/components/ProtectedRoute";
import { PurchaseRequestWorkspace } from "@/components/PurchaseRequestWorkspace";

export default function BppWorkflowPage() {
  return (
    <ProtectedRoute requiredPermission="workflow.bpp.submit">
      <PurchaseRequestWorkspace
        title="BPP Purchasing"
        workflowCode="BPP_PURCHASING"
      />
    </ProtectedRoute>
  );
}
