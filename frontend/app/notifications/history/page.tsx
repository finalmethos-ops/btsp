import { NotificationHistoryPanel } from "@/components/NotificationHistoryPanel";
import { ProtectedRoute } from "@/components/ProtectedRoute";

export default function NotificationHistoryPage() {
  return (
    <ProtectedRoute requiredPermission="notifications.read">
      <main className="mx-auto max-w-4xl p-6">
        <NotificationHistoryPanel />
      </main>
    </ProtectedRoute>
  );
}
