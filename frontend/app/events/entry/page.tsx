"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import {
  EventBrandingProvider,
  useEventBranding,
} from "@/components/EventBrandingProvider";
import { ProtectedRoute } from "@/components/ProtectedRoute";
import { listMyEvents, ManagedEvent } from "@/lib/event-admin-api";
import { useAuth } from "@/lib/auth";
import { eventLandingPath } from "@/lib/event-landing";

export default function EventEntryPage() {
  return (
    <ProtectedRoute loginMode="event">
      <EventBrandingProvider>
        <EventEntry />
      </EventBrandingProvider>
    </ProtectedRoute>
  );
}

function EventEntry() {
  const router = useRouter();
  const { user, selectEventVendor } = useAuth();
  const { brandedClassName, brandedStyle } = useEventBranding();
  const [events, setEvents] = useState<ManagedEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedEvent, setSelectedEvent] = useState<ManagedEvent | null>(null);
  const [vendorBusy, setVendorBusy] = useState<string | null>(null);

  function goToEvent(eventId: string) {
    // A full navigation also clears any stale entry-page state held by the
    // dev router/browser back-forward cache.
    window.location.assign(eventLandingPath(user, eventId));
  }

  useEffect(() => {
    if (!user) return;
    if (user.login_context !== "event") {
      router.replace("/event-login");
      return;
    }
    let active = true;
    void listMyEvents()
      .then((items) => {
        if (!active) return;
        // The API normally returns one row per event. Deduplicate defensively
        // because joined membership data (or an older cached response) can
        // otherwise make a single registration look like multiple events.
        const available = Array.from(
          new Map(
            items
              .filter(
                (event) => !["completed", "cancelled"].includes(event.status),
              )
              .map((event) => [event.id, event] as const),
          ).values(),
        );
        setEvents(available);
      })
      .catch((caught: unknown) => {
        if (active) {
          setError(
            caught instanceof Error
              ? caught.message
              : "Event registrations could not be loaded",
          );
        }
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [router, user]);

  if (loading) {
    return <main className="loading-screen">Opening your event…</main>;
  }

  async function openEvent(event: ManagedEvent) {
    const membership = event.memberships.find(
      (item) => item.email.toLowerCase() === user?.email?.toLowerCase(),
    );
    const vendorCodes =
      membership?.vendor_codes ??
      (membership?.vendor_code ? [membership.vendor_code] : []);
    if (membership?.membership_type === "vendor" && vendorCodes.length > 1) {
      setSelectedEvent(event);
      return;
    }
    goToEvent(event.id);
  }

  async function chooseVendor(vendorCode: string) {
    if (!selectedEvent) return;
    setVendorBusy(vendorCode);
    try {
      await selectEventVendor(selectedEvent.id, vendorCode);
      goToEvent(selectedEvent.id);
    } catch (caught) {
      setError(
        caught instanceof Error ? caught.message : "Vendor selection failed",
      );
    } finally {
      setVendorBusy(null);
    }
  }

  function vendorAccountForCode(code: string) {
    const normalized = code.replace(/[^a-z0-9]/gi, "").toUpperCase();
    const codeParts = code
      .toUpperCase()
      .split(/[^A-Z0-9]+/)
      .filter((part) => part.length >= 3);
    return user?.vendor_accounts.find((account) => {
      const accountCode = account.vendor_code.toUpperCase();
      if (accountCode === code.toUpperCase()) return true;
      const accountName = account.name.replace(/[^a-z0-9]/gi, "").toUpperCase();
      return (
        normalized === accountName ||
        normalized.includes(accountName) ||
        accountName.includes(normalized) ||
        codeParts.some(
          (part) => part === accountName || accountName.includes(part),
        )
      );
    });
  }

  return (
    <main className="event-ui mx-auto min-h-[70vh] max-w-5xl p-4 sm:p-8">
      <p className="brand-eyebrow">Event access</p>
      <h1 className="text-3xl font-bold">Select your event</h1>
      <p className="mt-2 text-slate-300">
        Choose the event workspace you want to enter. Only your current event
        registrations are shown.
      </p>
      {error ? (
        <p className="mt-5 rounded-xl bg-red-950 p-4 text-red-100">{error}</p>
      ) : null}
      {!error && !events.length ? (
        <p className="event-glass-pane mt-6 rounded-2xl p-6">
          You do not currently have an event available. The event may not have
          started yet, may have ended, or your registration may be inactive.
        </p>
      ) : null}
      <div className="mt-6 grid gap-4 sm:grid-cols-2">
        {events.map((event) => (
          <button
            className={brandedClassName(
              event.id,
              "event-glass-pane rounded-2xl p-5 text-left",
            )}
            key={event.id}
            onClick={() => void openEvent(event)}
            style={brandedStyle(event.id)}
            type="button"
          >
            <span className="brand-eyebrow">{event.status}</span>
            <strong className="mt-2 block text-xl">{event.name}</strong>
            <span className="mt-2 block text-sm">
              {event.venue_name} · {event.city}, {event.state_code}
            </span>
            <span className="mt-3 block text-sm font-bold">Open event →</span>
          </button>
        ))}
      </div>
      {selectedEvent ? (
        <section className="event-glass-pane mt-6 rounded-2xl p-5">
          <h2 className="text-xl font-bold">Select vendor account</h2>
          <p className="mt-1 text-sm text-slate-300">
            Choose the approved vendor account to use for {selectedEvent.name}.
          </p>
          <div className="mt-4 grid gap-3 sm:grid-cols-2">
            {(
              selectedEvent.memberships.find(
                (item) =>
                  item.email.toLowerCase() === user?.email?.toLowerCase(),
              )?.vendor_codes ?? []
            ).map((code) => (
              <button
                className="event-glass-pane rounded-xl p-4 text-left"
                disabled={vendorBusy !== null}
                key={code}
                onClick={() => void chooseVendor(code)}
                type="button"
              >
                <strong>{vendorAccountForCode(code)?.name ?? code}</strong>
                {vendorAccountForCode(code) ? (
                  <span className="mt-1 block text-xs text-slate-300">
                    {vendorAccountForCode(code)?.vendor_code}
                  </span>
                ) : null}
                <span className="mt-1 block text-sm">
                  {vendorBusy === code ? "Opening…" : "Open vendor account →"}
                </span>
              </button>
            ))}
          </div>
        </section>
      ) : null}
    </main>
  );
}
