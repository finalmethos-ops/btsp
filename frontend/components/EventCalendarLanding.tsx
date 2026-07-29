"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useEventBranding } from "@/components/EventBrandingProvider";
import { useEventScope } from "@/components/EventScopeProvider";
import { useAuth } from "@/lib/auth";
import {
  EventCalendarEntry,
  listMyEventCalendar,
} from "@/lib/event-calendar-api";
import {
  calendarEntryTiming,
  eventCalendarFilename,
  eventCalendarIcs,
} from "@/lib/event-calendar";
import { cacheEventData, readCachedEventData } from "@/lib/event-offline-cache";
import { useOnlineStatus } from "@/lib/use-online-status";
import { liveEventDestination } from "@/lib/live-event-destination";

function entryActions(
  entry: EventCalendarEntry,
  user: ReturnType<typeof useAuth>["user"],
) {
  if (!entry.sub_event_id || entry.sub_event_accessible === false) return [];
  const eventOperator = Boolean(
    user?.roles.some((role) => ["ADMIN", "SYSTEM_ADMIN"].includes(role)),
  );
  if (eventOperator) {
    return [
      {
        href: `/events/sub-event/${entry.sub_event_id}`,
        label: "Open event module",
      },
    ];
  }
  if (entry.module_codes.includes("live-display")) {
    return [
      {
        href: liveEventDestination(user, entry.event_id, entry.sub_event_id),
        label: "Join event",
      },
    ];
  }
  const actions: { href: string; label: string }[] = [];
  if (entry.module_codes.includes("vendor-buy-fair")) {
    if (!user?.roles.includes("VENDOR")) {
      return [
        {
          href: `/events/vendor-hall/${encodeURIComponent(entry.event_id)}`,
          label: "Join event",
        },
      ];
    }
    actions.push({
      href: `/events/buy-fair/${entry.sub_event_id}`,
      label: "Open vendor buy fair",
    });
  }
  if (
    user?.roles.includes("FRANCHISE_OPERATOR") &&
    entry.module_codes.includes("ordering")
  ) {
    actions.push({
      href: `/events/order/${entry.sub_event_id}`,
      label: "Open ordering",
    });
  }
  if (
    entry.module_codes.includes("store-loadout") &&
    !user?.roles.includes("VENDOR")
  ) {
    actions.push({
      href: `/events/sub-event/${entry.sub_event_id}`,
      label: "Open loadout",
    });
  }
  if (
    entry.module_codes.some((code) =>
      ["vendor-booths", "vendor-hall-setup", "vendor-hall-inventory"].includes(
        code,
      ),
    )
  ) {
    actions.push({
      href: `/events/sub-event/${entry.sub_event_id}`,
      label: "Open Booth Setup",
    });
  }
  return actions;
}

export function EventCalendarLanding({
  primary = false,
}: {
  primary?: boolean;
}) {
  const { brandedClassName, brandedStyle } = useEventBranding();
  const { user } = useAuth();
  const eventId = useEventScope();
  const [entries, setEntries] = useState<EventCalendarEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [now, setNow] = useState(() => new Date());
  const [offlineSnapshot, setOfflineSnapshot] = useState(false);
  const online = useOnlineStatus();
  useEffect(() => {
    let active = true;
    setLoading(true);
    const refresh = () =>
      void listMyEventCalendar()
        .then((items) => {
          const scopedItems = eventId
            ? items.filter((item) => item.event_id === eventId)
            : items;
          if (scopedItems.length) {
            const expiresAt = scopedItems.reduce(
              (latest, item) =>
                new Date(item.ends_at).getTime() > new Date(latest).getTime()
                  ? item.ends_at
                  : latest,
              scopedItems[0].ends_at,
            );
            cacheEventData("calendar", scopedItems, expiresAt);
          }
          if (active) {
            setEntries(scopedItems);
            setOfflineSnapshot(false);
          }
        })
        .catch(() => {
          const cached = readCachedEventData<EventCalendarEntry[]>("calendar");
          if (active && cached?.length) {
            setEntries(
              eventId
                ? cached.filter((item) => item.event_id === eventId)
                : cached,
            );
            setOfflineSnapshot(true);
          }
        })
        .finally(() => {
          if (active) setLoading(false);
        });
    refresh();
    const timer = window.setInterval(refresh, 60_000);
    return () => {
      active = false;
      window.clearInterval(timer);
    };
  }, [eventId]);
  useEffect(() => {
    const timer = window.setInterval(() => setNow(new Date()), 30_000);
    return () => window.clearInterval(timer);
  }, []);

  function downloadSchedule() {
    const calendar = new Blob([eventCalendarIcs(entries)], {
      type: "text/calendar;charset=utf-8",
    });
    const url = URL.createObjectURL(calendar);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = eventCalendarFilename(
      entries[0]?.event_name ?? "BTSP event",
    );
    anchor.click();
    window.setTimeout(() => URL.revokeObjectURL(url), 0);
  }
  if (loading)
    return (
      <section className="event-ui mx-auto max-w-4xl rounded-2xl border bg-white p-8 text-center">
        <p className="brand-eyebrow">Event schedule</p>
        <p className="mt-2 text-slate-300">Loading event schedule…</p>
      </section>
    );
  if (!entries.length)
    return primary ? (
      <section className="event-ui mx-auto max-w-4xl rounded-2xl border bg-white p-8 text-center">
        <p className="brand-eyebrow">Event access unavailable</p>
        <h1 className="mt-2 text-3xl font-bold">No event is currently open</h1>
        <p className="mt-3 text-slate-600">
          Your event calendar becomes available when the event begins and closes
          when the event ends.
        </p>
      </section>
    ) : null;
  const chronologicalEntries = [...entries].sort(
    (left, right) =>
      new Date(left.starts_at).getTime() - new Date(right.starts_at).getTime(),
  );
  const groups = Object.entries(
    chronologicalEntries.reduce<Record<string, EventCalendarEntry[]>>(
      (current, entry) => {
        const day = new Date(entry.starts_at).toLocaleDateString([], {
          weekday: "long",
          month: "long",
          day: "numeric",
        });
        const key = `${entry.event_name} · ${day}`;
        (current[key] ??= []).push(entry);
        return current;
      },
      {},
    ),
  );
  return (
    <section
      className={`event-ui event-calendar-schedule ${primary ? "mx-auto max-w-6xl" : "mb-6"} rounded-2xl border bg-white p-5`}
    >
      <div className="event-calendar-toolbar flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="brand-eyebrow">Your show schedule</p>
          <h2 className="text-2xl font-bold">Event calendar</h2>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          {offlineSnapshot ? (
            <span className="event-offline-badge">Offline schedule</span>
          ) : null}
          <span className="text-sm text-slate-500">Updates automatically</span>
          <button
            className="rounded-lg border border-blue-800 px-3 py-2 text-sm font-bold text-blue-900"
            onClick={downloadSchedule}
            type="button"
          >
            Add schedule to calendar
          </button>
        </div>
      </div>
      <div className="mt-4 space-y-5">
        {groups.map(([label, items]) => (
          <div key={label}>
            <h3 className="border-b pb-2 font-bold text-blue-900">{label}</h3>
            <div className="mt-3 grid gap-3 lg:grid-cols-2">
              {items.map((entry) => {
                const actions = entryActions(entry, user);
                const timing = calendarEntryTiming(entry, now);
                return (
                  <article
                    className={brandedClassName(
                      entry.event_id,
                      "event-calendar-card flex h-full flex-col rounded-xl border-l-4 border-blue-700 bg-slate-50 p-4",
                    )}
                    key={entry.id}
                    style={brandedStyle(entry.event_id)}
                  >
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <p className="text-xs font-bold uppercase text-blue-700">
                        {new Date(entry.starts_at).toLocaleTimeString([], {
                          hour: "numeric",
                          minute: "2-digit",
                        })}{" "}
                        –{" "}
                        {new Date(entry.ends_at).toLocaleTimeString([], {
                          hour: "numeric",
                          minute: "2-digit",
                        })}
                      </p>
                      {timing !== "past" ? (
                        <span
                          className={`event-calendar-timing rounded-full px-2.5 py-1 text-xs font-black uppercase ${
                            timing === "live" ? "is-live" : "is-upcoming"
                          }`}
                        >
                          {timing === "live" ? "Live now" : "Upcoming"}
                        </span>
                      ) : null}
                    </div>
                    <h4 className="font-bold">{entry.title}</h4>
                    {entry.sub_event_id &&
                    entry.sub_event_accessible === false ? (
                      <p className="mt-2 text-sm font-bold text-amber-700">
                        Not registered for this sub-event
                      </p>
                    ) : null}
                    {entry.location ? (
                      <p className="text-sm text-slate-600">{entry.location}</p>
                    ) : null}
                    {entry.description ? (
                      <p className="mt-2 text-sm text-slate-600">
                        {entry.description}
                      </p>
                    ) : null}
                    {actions.length ? (
                      <div className="event-calendar-actions mt-3 flex flex-wrap gap-2">
                        {actions.map((action) =>
                          online ? (
                            <Link
                              className="brand-button"
                              href={action.href}
                              key={action.href}
                            >
                              {action.label}
                            </Link>
                          ) : (
                            <span
                              className="brand-button is-offline-disabled"
                              key={action.href}
                            >
                              {action.label} · Online required
                            </span>
                          ),
                        )}
                      </div>
                    ) : null}
                  </article>
                );
              })}
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
