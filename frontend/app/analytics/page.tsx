import { AnalyticsDashboard } from "@/components/AnalyticsDashboard";
import { ProtectedRoute } from "@/components/ProtectedRoute";

export default function AnalyticsPage() {
  return (
    <ProtectedRoute requiredPermission="analytics.read">
      <AnalyticsDashboard />
    </ProtectedRoute>
  );
}
