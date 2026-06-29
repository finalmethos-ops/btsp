import { InvoiceWorkspace } from "@/components/InvoiceWorkspace";
import { ProtectedRoute } from "@/components/ProtectedRoute";

export default function InvoicesPage() {
  return (
    <ProtectedRoute requiredPermission="invoices.read">
      <InvoiceWorkspace />
    </ProtectedRoute>
  );
}
