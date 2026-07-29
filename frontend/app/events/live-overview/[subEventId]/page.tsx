"use client";

import { useParams } from "next/navigation";
import { EventLiveInsightsLanding } from "@/components/EventLiveInsightsLanding";
import { EventBrandingProvider } from "@/components/EventBrandingProvider";
import { ProtectedRoute } from "@/components/ProtectedRoute";

export default function EventLiveOverviewPage() {
  const params = useParams<{ subEventId: string }>();
  return (
    <ProtectedRoute loginMode="event">
      <EventBrandingProvider>
        <main className="event-ui mx-auto min-h-screen max-w-6xl p-4 sm:p-8">
          <p className="brand-eyebrow">Live event overview</p>
          <h1 className="text-3xl font-bold">Vendor presentation results</h1>
          <p className="mt-2 text-slate-300">
            Track your products, units sold, committed revenue, and position in
            the presentation queue. The live slideshow is projector-only.
          </p>
          <div className="mt-6">
            <EventLiveInsightsLanding subEventId={params.subEventId} />
          </div>
        </main>
      </EventBrandingProvider>
    </ProtectedRoute>
  );
}
