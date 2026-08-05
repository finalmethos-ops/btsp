"use client";

import { useParams, useRouter } from "next/navigation";
import { useEffect } from "react";
import { EventBrandingProvider } from "@/components/EventBrandingProvider";
import { EventVendorHallDirectory } from "@/components/EventVendorHallDirectory";
import { EventScopeProvider } from "@/components/EventScopeProvider";
import { ProtectedRoute } from "@/components/ProtectedRoute";
import { useAuth } from "@/lib/auth";

export default function EventVendorHallMapPage() {
  const params = useParams<{ eventId: string }>();
  return (
    <ProtectedRoute loginMode="event">
      <AttendeeVendorHallMap eventId={params.eventId} />
    </ProtectedRoute>
  );
}

function AttendeeVendorHallMap({ eventId }: { eventId: string }) {
  const { user } = useAuth();
  const router = useRouter();
  const restricted = Boolean(
    user?.roles.some((role) =>
      ["ADMIN", "SYSTEM_ADMIN", "VENDOR"].includes(role),
    ),
  );
  useEffect(() => {
    if (restricted)
      router.replace(
        `/events/calendar?event_id=${encodeURIComponent(eventId)}`,
      );
  }, [eventId, restricted, router]);
  if (restricted)
    return <main className="loading-screen">Opening event home…</main>;
  return (
    <EventBrandingProvider>
      <EventScopeProvider eventId={eventId}>
        <main className="event-ui mx-auto min-h-screen max-w-7xl p-4 sm:p-8">
          <p className="brand-eyebrow">Attendee event map</p>
          <h1 className="text-3xl font-bold">Vendor hall map</h1>
          <p className="mt-2 text-slate-300">
            Browse booths, save vendors to your visit list, and send meeting
            inquiries. Inventory and booth operations remain restricted to
            assigned users.
          </p>
          <div className="mt-6">
            <EventVendorHallDirectory eventId={eventId} />
          </div>
        </main>
      </EventScopeProvider>
    </EventBrandingProvider>
  );
}
