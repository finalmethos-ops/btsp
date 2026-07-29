import { AnalyticsDashboard } from "@/components/AnalyticsDashboard";
import { ProtectedRoute } from "@/components/ProtectedRoute";

export default function VendorPerformancePage() {
  return (
    <ProtectedRoute requiredPermission="analytics.read">
      <AnalyticsDashboard mode="vendor" />
    </ProtectedRoute>
  );
}
