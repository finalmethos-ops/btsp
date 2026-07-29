"use client";

import { useEffect, useState } from "react";
import { useEventBranding } from "@/components/EventBrandingProvider";
import { useEventScope } from "@/components/EventScopeProvider";
import {
  EventAnnouncement,
  listMyEventAnnouncements,
} from "@/lib/event-announcement-api";

const tone = {
  info: "border-blue-300 bg-blue-50 text-blue-950",
  important: "border-amber-300 bg-amber-50 text-amber-950",
  urgent: "border-red-400 bg-red-50 text-red-950",
};

const label = {
  info: "Announcement",
  important: "Important update",
  urgent: "Urgent alert",
};

export function EventAnnouncementLanding() {
  const { brandedClassName, brandedStyle } = useEventBranding();
  const eventId = useEventScope();
  const [announcements, setAnnouncements] = useState<EventAnnouncement[]>([]);
  useEffect(() => {
    let active = true;
    const refresh = () =>
      void listMyEventAnnouncements()
        .then((items) => {
          if (active) {
            setAnnouncements(
              eventId
                ? items.filter((item) => item.event_id === eventId)
                : items,
            );
          }
        })
        .catch(() => undefined);
    refresh();
    const timer = window.setInterval(refresh, 60_000);
    return () => {
      active = false;
      window.clearInterval(timer);
    };
  }, [eventId]);
  if (!announcements.length) return null;
  return (
    <section className="event-ui mb-6 space-y-3">
      {announcements.map((announcement) => (
        <article
          className={brandedClassName(
            announcement.event_id,
            `event-calendar-announcement rounded-2xl border-l-4 p-5 shadow-sm ${tone[announcement.severity]}`,
          )}
          key={announcement.id}
          style={brandedStyle(announcement.event_id)}
        >
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <p className="text-xs font-black uppercase tracking-[0.22em]">
                {label[announcement.severity]} · {announcement.event_name}
              </p>
              <h2 className="mt-1 text-xl font-bold">{announcement.title}</h2>
            </div>
            {announcement.sub_event_name ? (
              <span className="rounded-full bg-white/80 px-3 py-1 text-xs font-bold">
                {announcement.sub_event_name}
              </span>
            ) : null}
          </div>
          <p className="mt-2 whitespace-pre-wrap text-sm">
            {announcement.body}
          </p>
        </article>
      ))}
    </section>
  );
}
