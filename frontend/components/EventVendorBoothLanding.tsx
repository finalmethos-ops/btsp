"use client";

import { FormEvent, useEffect, useState } from "react";
import { useEventBranding } from "@/components/EventBrandingProvider";
import { useEventScope } from "@/components/EventScopeProvider";
import {
  EventVendorBooth,
  EventVendorBoothWrite,
  listMyEventVendorBooths,
  updateMyEventVendorBooth,
} from "@/lib/event-vendor-booth-api";

function writeFromBooth(
  booth: EventVendorBooth,
  data: FormData,
): EventVendorBoothWrite {
  return {
    vendor_code: booth.vendor_code,
    booth_name: String(data.get("booth_name")),
    booth_number: String(data.get("booth_number") || "") || null,
    location: String(data.get("location") || "") || null,
    description: String(data.get("description") || "") || null,
    contact_name: String(data.get("contact_name") || "") || null,
    contact_email: String(data.get("contact_email") || "") || null,
    website_url: String(data.get("website_url") || "") || null,
    status: booth.status,
  };
}

export function EventVendorBoothLanding() {
  const { brandedClassName, brandedStyle } = useEventBranding();
  const eventId = useEventScope();
  const [booths, setBooths] = useState<EventVendorBooth[]>([]);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    void listMyEventVendorBooths()
      .then((items) => {
        if (active) {
          setBooths(
            eventId ? items.filter((item) => item.event_id === eventId) : items,
          );
        }
      })
      .catch(() => undefined);
    return () => {
      active = false;
    };
  }, [eventId]);

  async function save(
    booth: EventVendorBooth,
    formEvent: FormEvent<HTMLFormElement>,
  ) {
    formEvent.preventDefault();
    setBusyId(booth.id);
    try {
      const updated = await updateMyEventVendorBooth(
        booth.id,
        writeFromBooth(booth, new FormData(formEvent.currentTarget)),
      );
      setBooths((current) =>
        current.map((item) => (item.id === updated.id ? updated : item)),
      );
      setEditingId(null);
    } finally {
      setBusyId(null);
    }
  }

  if (!booths.length) return null;

  return (
    <section className="event-ui event-vendor-booth-panel mb-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="brand-eyebrow">Vendor booth</p>
          <h2>Your event booth profile</h2>
          <p>Keep the show-facing details current for event attendees.</p>
        </div>
      </div>
      <div className="event-vendor-booth-grid">
        {booths.map((booth) => {
          const editing = editingId === booth.id;
          return (
            <article
              className={brandedClassName(
                booth.event_id,
                "event-vendor-booth-card",
              )}
              key={booth.id}
              style={brandedStyle(booth.event_id)}
            >
              {editing ? (
                <form
                  className="event-vendor-booth-form"
                  onSubmit={(event) => void save(booth, event)}
                >
                  <p className="brand-eyebrow">{booth.event_name}</p>
                  <input
                    defaultValue={booth.booth_name}
                    name="booth_name"
                    placeholder="Booth name"
                    required
                  />
                  <div className="event-vendor-booth-fields">
                    <input
                      defaultValue={booth.booth_number ?? ""}
                      name="booth_number"
                      placeholder="Booth #"
                    />
                    <input
                      defaultValue={booth.location ?? ""}
                      name="location"
                      placeholder="Location"
                    />
                  </div>
                  <textarea
                    defaultValue={booth.description ?? ""}
                    name="description"
                    placeholder="Booth description"
                  />
                  <div className="event-vendor-booth-fields">
                    <input
                      defaultValue={booth.contact_name ?? ""}
                      name="contact_name"
                      placeholder="Contact name"
                    />
                    <input
                      defaultValue={booth.contact_email ?? ""}
                      name="contact_email"
                      placeholder="Contact email"
                      type="email"
                    />
                  </div>
                  <input
                    defaultValue={booth.website_url ?? ""}
                    name="website_url"
                    placeholder="Website URL"
                    type="url"
                  />
                  <div className="event-vendor-booth-actions">
                    <button
                      className="brand-button"
                      disabled={busyId === booth.id}
                    >
                      Save booth
                    </button>
                    <button
                      className="brand-button brand-button-secondary"
                      onClick={() => setEditingId(null)}
                      type="button"
                    >
                      Cancel
                    </button>
                  </div>
                </form>
              ) : (
                <>
                  <div>
                    <p className="brand-eyebrow">{booth.event_name}</p>
                    <h3>{booth.booth_name}</h3>
                    <p>
                      {booth.booth_number ?? "No booth #"} ·{" "}
                      {booth.location ?? "Location TBD"}
                    </p>
                    {booth.description ? <p>{booth.description}</p> : null}
                  </div>
                  <div className="event-vendor-booth-meta">
                    <span>{booth.vendor_name ?? booth.vendor_code}</span>
                    <span>{booth.contact_name ?? "Contact TBD"}</span>
                    {booth.contact_email ? (
                      <span>{booth.contact_email}</span>
                    ) : null}
                  </div>
                  <button
                    className="brand-button"
                    onClick={() => setEditingId(booth.id)}
                    type="button"
                  >
                    Edit booth profile
                  </button>
                </>
              )}
            </article>
          );
        })}
      </div>
    </section>
  );
}
