import { AnalyticsDashboard } from "@/components/AnalyticsDashboard";
import { ProtectedRoute } from "@/components/ProtectedRoute";

export default function ReportsPage() {
  return (
    <ProtectedRoute requiredPermission="analytics.read">
      <AnalyticsDashboard mode="reports" />
    </ProtectedRoute>
  );
}
