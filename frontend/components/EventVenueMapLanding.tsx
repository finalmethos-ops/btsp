"use client";

import { useEffect, useState } from "react";
import { ManagedEvent, downloadEventVenueMap } from "@/lib/event-admin-api";

export function EventVenueMapLanding({ event }: { event: ManagedEvent }) {
  const [sourceUrl, setSourceUrl] = useState<string | null>(null);
  const [contentType, setContentType] = useState<string | null>(null);

  useEffect(() => {
    if (!event.has_venue_map) return;
    let active = true;
    let url: string | null = null;
    void downloadEventVenueMap(event.id)
      .then((blob) => {
        if (!active) return;
        url = URL.createObjectURL(blob);
        setSourceUrl(url);
        setContentType(blob.type);
      })
      .catch(() => {
        if (active) setSourceUrl(null);
      });
    return () => {
      active = false;
      if (url) URL.revokeObjectURL(url);
    };
  }, [event.has_venue_map, event.id]);

  if (!event.has_venue_map || !sourceUrl) return null;
  const pdf = contentType === "application/pdf";
  return (
    <section className="event-ui event-venue-map mb-6 rounded-2xl border bg-white p-4 sm:p-5">
      <p className="brand-eyebrow">Venue overview</p>
      <h2 className="text-2xl font-bold">{event.venue_name} map</h2>
      <p className="mb-4 text-sm text-slate-600">
        Read-only venue map for orientation. Booth operations are available only
        from their assigned event modules.
      </p>
      {pdf ? (
        <iframe
          className="h-[70vh] min-h-96 w-full rounded-xl border"
          src={sourceUrl}
          title={`${event.name} venue map`}
        />
      ) : (
        // eslint-disable-next-line @next/next/no-img-element
        <img
          alt={`${event.name} venue map`}
          className="max-h-[70vh] w-full rounded-xl border object-contain"
          src={sourceUrl}
        />
      )}
    </section>
  );
}
