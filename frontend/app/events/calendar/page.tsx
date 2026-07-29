"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { EventBrandingProvider } from "@/components/EventBrandingProvider";
import { EventScopeProvider } from "@/components/EventScopeProvider";
import { EventAnnouncementLanding } from "@/components/EventAnnouncementLanding";
import { EventCalendarLanding } from "@/components/EventCalendarLanding";
import { EventPassLanding } from "@/components/EventPassLanding";
import { EventSummaryLanding } from "@/components/EventSummaryLanding";
import { EventVenueMapLanding } from "@/components/EventVenueMapLanding";
import { EventWelcomeBanner } from "@/components/EventWelcomeBanner";
import { ProtectedRoute } from "@/components/ProtectedRoute";
import { useAuth } from "@/lib/auth";
import { listMyEvents, ManagedEvent } from "@/lib/event-admin-api";

export default function EventCalendarPage() {
  return (
    <ProtectedRoute loginMode="event">
      <EventCalendarHome />
    </ProtectedRoute>
  );
}

function EventCalendarHome() {
  const { user, selectEventVendor } = useAuth();
  const router = useRouter();
  const [event, setEvent] = useState<ManagedEvent | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [vendorSwitchOpen, setVendorSwitchOpen] = useState(false);
  const [switchingVendor, setSwitchingVendor] = useState<string | null>(null);

  useEffect(() => {
    if (!user) return;
    if (user.login_context !== "event") {
      router.replace("/event-login");
      return;
    }
    const eventId = new URLSearchParams(window.location.search).get("event_id");
    let active = true;
    void listMyEvents()
      .then((events) => {
        if (!active) return;
        const selected = eventId
          ? events.find((item) => item.id === eventId)
          : events[0];
        if (!selected) {
          router.replace("/events/entry");
          return;
        }
        setEvent(selected);
      })
      .catch((caught: unknown) => {
        if (!active) return;
        setError(
          caught instanceof Error
            ? caught.message
            : "Your event workspace could not be loaded",
        );
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [router, user]);

  if (!user || user.login_context !== "event" || loading) {
    return <main className="loading-screen">Loading event access…</main>;
  }

  if (error || !event) {
    return (
      <main className="event-ui mx-auto max-w-2xl p-8">
        <section className="event-glass-pane rounded-2xl p-6">
          <p className="brand-eyebrow">Event access</p>
          <h1 className="text-2xl font-bold">Event workspace unavailable</h1>
          <p className="mt-2 text-slate-300">
            {error ?? "This event is no longer available for your account."}
          </p>
          <button
            className="brand-button mt-5"
            onClick={() => router.replace("/events/entry")}
            type="button"
          >
            Return to event access
          </button>
        </section>
      </main>
    );
  }

  const canSeeEventSummary = user.roles.some((role) =>
    ["VENDOR", "FRANCHISE_OPERATOR"].includes(role),
  );
  const canReviewEvent = user.roles.some((role) =>
    ["ADMIN", "SYSTEM_ADMIN", "EXECUTIVE"].includes(role),
  );

  return (
    <main className="event-ui min-h-screen bg-slate-950 p-4 sm:p-8">
      <EventBrandingProvider>
        <EventScopeProvider eventId={event.id}>
          <div className="mx-auto max-w-6xl">
            <div className="event-calendar-page-actions mb-4 flex flex-wrap justify-end gap-3">
              {user.roles.includes("VENDOR") &&
              user.vendor_accounts.length > 1 ? (
                <details
                  className="event-calendar-vendor-switch relative"
                  open={vendorSwitchOpen}
                  onToggle={(input) =>
                    setVendorSwitchOpen(input.currentTarget.open)
                  }
                >
                  <summary className="brand-button list-none cursor-pointer">
                    Switch vendor
                  </summary>
                  <div className="event-calendar-vendor-menu absolute right-0 z-20 mt-2 min-w-56 rounded-xl border border-slate-600 bg-slate-950 p-2 shadow-xl">
                    {user.vendor_accounts.map((account) => (
                      <button
                        className="block w-full rounded-lg px-3 py-2 text-left text-sm font-bold text-white hover:bg-white/10 disabled:opacity-60"
                        disabled={switchingVendor !== null}
                        key={account.vendor_code}
                        onClick={() => {
                          setSwitchingVendor(account.vendor_code);
                          void selectEventVendor(event.id, account.vendor_code)
                            .then(() => setVendorSwitchOpen(false))
                            .finally(() => setSwitchingVendor(null));
                        }}
                        type="button"
                      >
                        {account.name} · {account.vendor_code}
                        {account.vendor_code === user.active_vendor_code
                          ? " (current)"
                          : ""}
                      </button>
                    ))}
                  </div>
                </details>
              ) : null}
              {canReviewEvent ? (
                <a className="brand-button" href={`/events/review/${event.id}`}>
                  Full event review
                </a>
              ) : null}
              <button
                className="brand-button"
                onClick={() => router.push("/events/entry")}
                type="button"
              >
                Switch event
              </button>
            </div>
            <EventWelcomeBanner event={event} />
            {canSeeEventSummary ? (
              <EventSummaryLanding eventId={event.id} />
            ) : null}
            <div className="event-calendar-layout mt-6 grid gap-6 lg:grid-cols-[minmax(0,1.2fr)_minmax(18rem,0.8fr)] lg:items-start">
              <EventCalendarLanding primary />
              <aside className="event-ui event-calendar-announcements rounded-2xl border bg-white p-5">
                <p className="brand-eyebrow">Stay informed</p>
                <h2 className="text-2xl font-bold">Announcements & updates</h2>
                <div className="mt-4">
                  <EventAnnouncementLanding />
                </div>
              </aside>
            </div>
            <EventVenueMapLanding event={event} />
            <EventPassLanding />
          </div>
        </EventScopeProvider>
      </EventBrandingProvider>
    </main>
  );
}
