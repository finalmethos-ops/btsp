import { ProtectedRoute } from "@/components/ProtectedRoute";
import { ReceivingWorkspace } from "@/components/ReceivingWorkspace";

export default function ReceivingPage() {
  return (
    <ProtectedRoute requiredPermission="receiving.read">
      <ReceivingWorkspace />
    </ProtectedRoute>
  );
}
