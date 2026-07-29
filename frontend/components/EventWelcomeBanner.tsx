"use client";

import { ManagedEvent } from "@/lib/event-admin-api";
import {
  useEventBrandAsset,
  useEventBranding,
} from "@/components/EventBrandingProvider";

export function EventWelcomeBanner({ event }: { event: ManagedEvent }) {
  const { brandingUrl } = useEventBrandAsset(event.id);
  const { brandedClassName, brandedStyle } = useEventBranding();
  return (
    <section
      className={brandedClassName(
        "event-welcome-banner relative overflow-hidden rounded-3xl border p-6 text-white shadow-xl sm:p-8",
      )}
      style={brandedStyle(event.id)}
    >
      <div className="relative z-10 max-w-3xl">
        <p className="brand-eyebrow">Event workspace</p>
        <h1 className="mt-2 text-3xl font-black sm:text-5xl">
          Welcome to {event.name}
        </h1>
        <p className="mt-3 text-sm text-slate-200 sm:text-base">
          Your event schedule, announcements, venue orientation, and credentials
          are all in one place.
        </p>
        <p className="mt-4 text-sm font-semibold text-slate-300">
          {event.venue_name} · {event.city}, {event.state_code}
        </p>
      </div>
      {brandingUrl ? (
        // eslint-disable-next-line @next/next/no-img-element
        <img
          alt={`${event.name} logo`}
          className="event-welcome-logo pointer-events-none object-contain opacity-95"
          src={brandingUrl}
        />
      ) : null}
    </section>
  );
}
