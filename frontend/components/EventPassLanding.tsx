"use client";

import Image from "next/image";
import { useEffect, useState } from "react";
import QRCode from "qrcode";
import { useEventBranding } from "@/components/EventBrandingProvider";
import { useEventScope } from "@/components/EventScopeProvider";
import { useAuth } from "@/lib/auth";
import {
  EventAttendancePass,
  getMyEventPasses,
} from "@/lib/event-attendance-api";
import { hasPermission } from "@/lib/permissions";
import { cacheEventData, readCachedEventData } from "@/lib/event-offline-cache";

const statusLabel = {
  registered: "Registered",
  checked_in: "Checked in",
  checked_out: "Checked out",
};

function categoryLabel(value: EventAttendancePass["membership_type"]) {
  return value.replaceAll("_", " ");
}

function formatSubEventTime(start: string) {
  return new Date(start).toLocaleString([], {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

export function EventPassLanding() {
  const { user } = useAuth();
  const { brandedClassName, brandedStyle } = useEventBranding();
  const eventId = useEventScope();
  const [passes, setPasses] = useState<EventAttendancePass[]>([]);
  const [qrCodes, setQrCodes] = useState<Record<string, string>>({});
  const [offlineSnapshot, setOfflineSnapshot] = useState(false);
  const shouldLoad = Boolean(user && !hasPermission(user, "events.manage"));

  useEffect(() => {
    if (!shouldLoad) return;
    let active = true;
    const refresh = () =>
      void getMyEventPasses()
        .then((items) => {
          const scopedItems = eventId
            ? items.filter((item) => item.event_id === eventId)
            : items;
          const endsAt = scopedItems
            .flatMap((pass) => pass.sub_events.map((item) => item.ends_at))
            .sort(
              (left, right) =>
                new Date(right).getTime() - new Date(left).getTime(),
            )[0];
          if (scopedItems.length && endsAt) {
            cacheEventData("passes", scopedItems, endsAt);
          }
          if (active) {
            setPasses(scopedItems);
            setOfflineSnapshot(false);
          }
        })
        .catch(() => {
          const cached = readCachedEventData<EventAttendancePass[]>("passes");
          if (active && cached?.length) {
            setPasses(
              eventId
                ? cached.filter((item) => item.event_id === eventId)
                : cached,
            );
            setOfflineSnapshot(true);
          }
        });
    refresh();
    const timer = window.setInterval(refresh, 60_000);
    return () => {
      active = false;
      window.clearInterval(timer);
    };
  }, [eventId, shouldLoad]);

  useEffect(() => {
    let active = true;
    void Promise.all(
      passes.map(async (pass) => [
        pass.membership_id,
        await QRCode.toDataURL(pass.pass_code, {
          errorCorrectionLevel: "M",
          margin: 1,
          width: 240,
        }),
      ]),
    ).then((items) => {
      if (active) setQrCodes(Object.fromEntries(items));
    });
    return () => {
      active = false;
    };
  }, [passes]);

  if (!shouldLoad || !passes.length) return null;

  return (
    <section className="event-ui event-pass-panel mb-6">
      <div>
        <p className="brand-eyebrow">Event pass</p>
        <h2>Your attendee credentials</h2>
        <p>
          Show this pass at staffed check-in points for your assigned sessions.
        </p>
        {offlineSnapshot ? (
          <span className="event-offline-badge">Offline pass</span>
        ) : null}
      </div>
      <div className="event-pass-grid">
        {passes.map((pass) => (
          <article
            className={brandedClassName(pass.event_id, "event-pass-card")}
            key={pass.membership_id}
            style={brandedStyle(pass.event_id)}
          >
            <div className="event-pass-card-header">
              <div>
                <p className="brand-eyebrow">{pass.event_name}</p>
                <h3>{pass.display_name}</h3>
                <p>{pass.email}</p>
              </div>
              <div aria-hidden="true" className="event-pass-mark" />
            </div>
            <dl className="event-pass-details">
              <div>
                <dt>Category</dt>
                <dd>{categoryLabel(pass.membership_type)}</dd>
              </div>
              <div>
                <dt>{pass.vendor_code ? "Vendor" : "Entity"}</dt>
                <dd>{pass.vendor_code ?? pass.entity_code ?? "Event staff"}</dd>
              </div>
            </dl>
            <div className="event-pass-code">
              <div>
                <span>Pass code</span>
                <strong>{pass.pass_code}</strong>
              </div>
              {qrCodes[pass.membership_id] ? (
                <Image
                  alt={`Check-in code for ${pass.display_name}`}
                  height={160}
                  src={qrCodes[pass.membership_id]}
                  unoptimized
                  width={160}
                />
              ) : null}
            </div>
            <div className="event-pass-sub-events">
              {pass.sub_events.map((subEvent) => (
                <div className="event-pass-sub-event" key={subEvent.id}>
                  <div>
                    <strong>{subEvent.name}</strong>
                    <p>
                      {subEvent.location} ·{" "}
                      {formatSubEventTime(subEvent.starts_at)}
                    </p>
                  </div>
                  <span
                    className={`event-pass-status event-pass-status-${subEvent.status}`}
                  >
                    {subEvent.check_in_enabled
                      ? statusLabel[subEvent.status]
                      : "No check-in"}
                  </span>
                </div>
              ))}
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}
