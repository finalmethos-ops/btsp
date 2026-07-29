"use client";

import { useParams, useRouter } from "next/navigation";
import { useEffect } from "react";
import { EventVendorBuyFairWorkspace } from "@/components/EventVendorBuyFairWorkspace";
import { ProtectedRoute } from "@/components/ProtectedRoute";
import { useAuth } from "@/lib/auth";
import { listMyEvents } from "@/lib/event-admin-api";

export default function EventVendorBuyFairPage() {
  const params = useParams<{ subEventId: string }>();
  return (
    <ProtectedRoute loginMode="event">
      <BuyFairEntry subEventId={params.subEventId} />
    </ProtectedRoute>
  );
}

function BuyFairEntry({ subEventId }: { subEventId: string }) {
  const { user } = useAuth();
  const router = useRouter();
  const vendor = Boolean(user?.roles.includes("VENDOR"));

  useEffect(() => {
    if (!user || vendor) return;
    let active = true;
    void listMyEvents()
      .then((events) => {
        if (!active) return;
        const event = events.find((item) =>
          item.sub_events.some((subEvent) => subEvent.id === subEventId),
        );
        router.replace(
          event
            ? `/events/vendor-hall/${encodeURIComponent(event.id)}`
            : "/events/entry",
        );
      })
      .catch(() => {
        if (active) router.replace("/events/entry");
      });
    return () => {
      active = false;
    };
  }, [router, subEventId, user, vendor]);

  if (!vendor)
    return <main className="loading-screen">Opening event map…</main>;
  return <EventVendorBuyFairWorkspace subEventId={subEventId} />;
}
