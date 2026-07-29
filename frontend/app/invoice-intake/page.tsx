import { InvoiceIntakeWorkspace } from "@/components/InvoiceIntakeWorkspace";
import { ProtectedRoute } from "@/components/ProtectedRoute";

export default function InvoiceIntakePage() {
  return (
    <ProtectedRoute>
      <InvoiceIntakeWorkspace />
    </ProtectedRoute>
  );
}
