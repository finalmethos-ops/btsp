"use client";

import { useParams } from "next/navigation";
import { EventPresenterMonitor } from "@/components/EventPresenterMonitor";
import { ProtectedRoute } from "@/components/ProtectedRoute";

export default function EventPresenterMonitorPage() {
  const params = useParams<{ subEventId: string }>();
  return (
    <ProtectedRoute loginMode="event" requiredPermission="events.manage">
      <EventPresenterMonitor subEventId={params.subEventId} />
    </ProtectedRoute>
  );
}
