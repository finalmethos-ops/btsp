"use client";

import { useParams } from "next/navigation";
import { EventOrderingPortal } from "@/components/EventOrderingPortal";
import { ProtectedRoute } from "@/components/ProtectedRoute";

export default function EventOrderPage() {
  const params = useParams<{ subEventId: string }>();
  return (
    <ProtectedRoute loginMode="event">
      <EventOrderingPortal subEventId={params.subEventId} />
    </ProtectedRoute>
  );
}
