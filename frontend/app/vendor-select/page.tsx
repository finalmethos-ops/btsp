import { ProtectedRoute } from "@/components/ProtectedRoute";
import { VendorAccountSelector } from "@/components/VendorAccountSelector";

export default function VendorSelectPage() {
  return (
    <ProtectedRoute>
      <VendorAccountSelector />
    </ProtectedRoute>
  );
}
