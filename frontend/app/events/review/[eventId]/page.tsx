"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { EventBrandingProvider } from "@/components/EventBrandingProvider";
import { EventScopeProvider } from "@/components/EventScopeProvider";
import { EventSummaryLanding } from "@/components/EventSummaryLanding";
import { ProtectedRoute } from "@/components/ProtectedRoute";
import { ManagedEvent, listMyEvents } from "@/lib/event-admin-api";
import { useAuth } from "@/lib/auth";

export default function EventReviewPage() {
  const params = useParams<{ eventId: string }>();
  return (
    <ProtectedRoute loginMode="event">
      <EventReviewWorkspace eventId={params.eventId} />
    </ProtectedRoute>
  );
}

function EventReviewWorkspace({ eventId }: { eventId: string }) {
  const { user } = useAuth();
  const router = useRouter();
  const [event, setEvent] = useState<ManagedEvent | null>(null);
  useEffect(() => {
    if (!user) return;
    if (
      !user.roles.some((role) =>
        ["ADMIN", "SYSTEM_ADMIN", "EXECUTIVE"].includes(role),
      )
    ) {
      router.replace(
        `/events/calendar?event_id=${encodeURIComponent(eventId)}`,
      );
      return;
    }
    void listMyEvents()
      .then((events) => {
        const match = events.find((item) => item.id === eventId);
        if (match) setEvent(match);
        else router.replace("/events/entry");
      })
      .catch(() => router.replace("/events/entry"));
  }, [eventId, router, user]);
  if (!event)
    return <main className="loading-screen">Loading event review…</main>;
  return (
    <EventBrandingProvider>
      <EventScopeProvider eventId={event.id}>
        <main className="event-ui mx-auto min-h-screen max-w-6xl p-4 sm:p-8">
          <button
            className="module-home-link mb-5"
            onClick={() => router.push(`/events/calendar?event_id=${event.id}`)}
            type="button"
          >
            ← Back to event calendar
          </button>
          <EventSummaryLanding eventId={event.id} reviewMode />
        </main>
      </EventScopeProvider>
    </EventBrandingProvider>
  );
}
