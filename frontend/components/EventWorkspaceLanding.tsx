"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { useEventBranding } from "@/components/EventBrandingProvider";
import { useAuth } from "@/lib/auth";
import {
  listMyEvents,
  ManagedEvent,
  ManagedSubEvent,
} from "@/lib/event-admin-api";
import { hasPermission } from "@/lib/permissions";
import { EventSummaryLanding } from "@/components/EventSummaryLanding";
import { liveEventDestination } from "@/lib/live-event-destination";

const moduleLabels: Record<string, string> = {
  "check-in": "Check-in",
  "live-display": "Live display",
  ordering: "Ordering",
  polling: "Live poll",
  "product-slides": "Product lineup",
  "staff-tasks": "Staff tasks",
  "vendor-booths": "Vendor booths",
  "vendor-hall-setup": "Vendor hall setup",
  "vendor-hall-inventory": "Vendor inventory",
  "event-inventory": "Event inventory suite",
  "vendor-buy-fair": "Vendor buy fair",
};

function formatRange(start: string, end: string) {
  const startsAt = new Date(start);
  const endsAt = new Date(end);
  return `${startsAt.toLocaleDateString([], {
    month: "short",
    day: "numeric",
  })} · ${startsAt.toLocaleTimeString([], {
    hour: "numeric",
    minute: "2-digit",
  })}–${endsAt.toLocaleTimeString([], {
    hour: "numeric",
    minute: "2-digit",
  })}`;
}

function nextSubEvent(events: ManagedEvent[]) {
  const now = Date.now();
  return events
    .flatMap((event) =>
      event.sub_events.map((subEvent) => ({
        event,
        subEvent,
        startsAt: new Date(subEvent.starts_at).getTime(),
      })),
    )
    .filter((item) => item.startsAt >= now)
    .sort((a, b) => a.startsAt - b.startsAt)[0];
}

function actionFor(
  event: ManagedEvent,
  subEvent: ManagedSubEvent,
  user: ReturnType<typeof useAuth>["user"],
) {
  const eventOperator = Boolean(
    user?.roles.some((role) => ["ADMIN", "SYSTEM_ADMIN"].includes(role)),
  );
  if (eventOperator) {
    return {
      href: `/events/sub-event/${subEvent.id}`,
      label: "Open event module",
    };
  }
  const franchiseRep = Boolean(user?.roles.includes("FRANCHISE_OPERATOR"));
  if (subEvent.module_codes.includes("live-display")) {
    return {
      href: liveEventDestination(user, event.id, subEvent.id),
      label: "Join event",
    };
  }
  if (subEvent.module_codes.includes("vendor-buy-fair")) {
    if (!user?.roles.includes("VENDOR")) {
      return {
        href: `/events/vendor-hall/${encodeURIComponent(event.id)}`,
        label: "Join event",
      };
    }
    return {
      href: `/events/buy-fair/${subEvent.id}`,
      label: "Open vendor buy fair",
    };
  }
  if (franchiseRep && subEvent.module_codes.includes("ordering")) {
    return {
      href: `/events/order/${subEvent.id}`,
      label: "Open ordering",
    };
  }
  return null;
}

export function EventWorkspaceLanding() {
  const { user } = useAuth();
  const { brandedClassName, brandedStyle } = useEventBranding();
  const [events, setEvents] = useState<ManagedEvent[]>([]);

  const shouldLoad = Boolean(user && !hasPermission(user, "events.manage"));

  useEffect(() => {
    if (!shouldLoad) return;
    let active = true;
    const refresh = () =>
      void listMyEvents()
        .then((items) => {
          if (active) setEvents(items);
        })
        .catch(() => undefined);
    refresh();
    const timer = window.setInterval(refresh, 60_000);
    return () => {
      active = false;
      window.clearInterval(timer);
    };
  }, [shouldLoad]);

  const upcoming = useMemo(() => nextSubEvent(events), [events]);
  const visibleSubEvents = events.flatMap((event) =>
    event.sub_events.map((subEvent) => ({ event, subEvent })),
  );

  if (!shouldLoad || !events.length) return null;

  return (
    <section className="event-ui event-hub-panel mb-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="brand-eyebrow">Event home</p>
          <h2>Your event hub</h2>
          <p>
            Your assigned events, live sessions, buying actions, and show tools
            are collected here.
          </p>
        </div>
        <Link className="brand-button" href="/events/entry">
          Open event home
        </Link>
      </div>

      {upcoming ? (
        <article
          className={brandedClassName(upcoming.event.id, "event-hub-next")}
          style={brandedStyle(upcoming.event.id)}
        >
          <div>
            <span className="brand-badge">Next up</span>
            <h3>{upcoming.subEvent.name}</h3>
            <p>
              {upcoming.event.name} · {upcoming.subEvent.location} ·{" "}
              {formatRange(
                upcoming.subEvent.starts_at,
                upcoming.subEvent.ends_at,
              )}
            </p>
          </div>
          {(() => {
            const action = actionFor(upcoming.event, upcoming.subEvent, user);
            return action ? (
              <Link className="brand-button" href={action.href}>
                {action.label}
              </Link>
            ) : null;
          })()}
        </article>
      ) : null}

      {events.slice(0, 3).map((event) => (
        <EventSummaryLanding eventId={event.id} key={`summary-${event.id}`} />
      ))}

      <div className="event-hub-grid">
        {visibleSubEvents.slice(0, 6).map(({ event, subEvent }) => {
          const action = actionFor(event, subEvent, user);
          return (
            <article
              className={brandedClassName(event.id, "event-hub-card")}
              key={subEvent.id}
              style={brandedStyle(event.id)}
            >
              <p className="brand-eyebrow">{event.name}</p>
              <h3>{subEvent.name}</h3>
              <p>
                {subEvent.location} ·{" "}
                {formatRange(subEvent.starts_at, subEvent.ends_at)}
              </p>
              <div className="mt-3 flex flex-wrap gap-2">
                {subEvent.module_codes
                  .filter((code) => code in moduleLabels)
                  .map((code) => (
                    <span className="event-hub-chip" key={code}>
                      {moduleLabels[code]}
                    </span>
                  ))}
              </div>
              {action ? (
                <Link className="event-hub-link" href={action.href}>
                  {action.label} →
                </Link>
              ) : null}
            </article>
          );
        })}
      </div>
    </section>
  );
}
