"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { EventPresentationDisplay } from "@/components/EventPresentationDisplay";
import { ProtectedRoute } from "@/components/ProtectedRoute";
import { useAuth } from "@/lib/auth";
import { listMyEvents } from "@/lib/event-admin-api";
import { liveEventDestination } from "@/lib/live-event-destination";
import { hasPermission } from "@/lib/permissions";

function EventPresentationEntry({ subEventId }: { subEventId: string }) {
  const { user } = useAuth();
  const router = useRouter();
  const [allowed, setAllowed] = useState<boolean | null>(null);

  useEffect(() => {
    if (!user) return;
    if (hasPermission(user, "events.manage")) {
      setAllowed(true);
      return;
    }
    let active = true;
    void listMyEvents()
      .then((events) => {
        const event = events.find((item) =>
          item.sub_events.some((subEvent) => subEvent.id === subEventId),
        );
        if (!active) return;
        router.replace(
          event
            ? liveEventDestination(user, event.id, subEventId)
            : "/events/calendar",
        );
      })
      .catch(() => {
        if (active) router.replace("/events/calendar");
      });
    return () => {
      active = false;
    };
  }, [router, subEventId, user]);

  if (allowed !== true)
    return <main className="loading-screen">Opening event tools…</main>;
  return <EventPresentationDisplay subEventId={subEventId} />;
}

export default function EventPresentationPage() {
  const params = useParams<{ subEventId: string }>();
  return (
    <ProtectedRoute
      loginMode="event"
      loginRedirectTo={`/events/present/${params.subEventId}`}
    >
      <EventPresentationEntry subEventId={params.subEventId} />
    </ProtectedRoute>
  );
}
