import { NotificationPreferencesPanel } from "@/components/NotificationPreferencesPanel";
import { ProtectedRoute } from "@/components/ProtectedRoute";
import Link from "next/link";

export default function NotificationPreferencesPage() {
  return (
    <ProtectedRoute requiredPermission="notifications.read">
      <main className="mx-auto max-w-3xl space-y-4 p-6">
        <NotificationPreferencesPanel />
        <Link
          className="inline-block rounded-lg border px-4 py-2 font-bold"
          href="/notifications/history"
        >
          View delivery history
        </Link>
      </main>
    </ProtectedRoute>
  );
}
