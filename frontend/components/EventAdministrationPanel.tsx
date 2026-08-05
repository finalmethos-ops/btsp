"use client";

import Link from "next/link";
import { FormEvent, useCallback, useEffect, useState } from "react";
import {
  addManagedSubEvent,
  cancelManagedEvent,
  createManagedEvent,
  deleteManagedEvent,
  deleteManagedSubEvent,
  downloadEventBranding,
  EventWrite,
  listManagedEvents,
  ManagedEvent,
  ManagedSubEvent,
  publishManagedEvent,
  updateManagedEvent,
  updateManagedSubEvent,
  uploadEventBranding,
  uploadEventVenueMap,
} from "@/lib/event-admin-api";

const iso = (value: FormDataEntryValue | null) =>
  new Date(String(value ?? "")).toISOString();
const localDateTime = (value: string) => {
  const date = new Date(value);
  const offset = date.getTimezoneOffset() * 60_000;
  return new Date(date.getTime() - offset).toISOString().slice(0, 16);
};

function eventPayload(data: FormData, existing?: ManagedEvent): EventWrite {
  return {
    name: String(data.get("name")),
    slug: String(data.get("slug")).trim().toLowerCase(),
    description: String(data.get("description") || "") || null,
    status: existing?.status ?? "draft",
    starts_at: iso(data.get("starts_at")),
    ends_at: iso(data.get("ends_at")),
    timezone: String(data.get("timezone")),
    venue_name: String(data.get("venue_name")),
    address_line1: String(data.get("address_line1")),
    address_line2: String(data.get("address_line2") || "") || null,
    city: String(data.get("city")),
    state_code: String(data.get("state_code")).toUpperCase(),
    postal_code: String(data.get("postal_code")),
    country_code: existing?.country_code ?? "US",
    theme_primary_color: String(data.get("theme_primary_color") || "#07142c"),
    theme_accent_color: String(data.get("theme_accent_color") || "#ffd400"),
  };
}

export function EventAdministrationPanel() {
  const [events, setEvents] = useState<ManagedEvent[]>([]);
  const [selected, setSelected] = useState<ManagedEvent | null>(null);
  const [brandingUrl, setBrandingUrl] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async (selectedId?: string) => {
    const next = await listManagedEvents();
    setEvents(next);
    setSelected(next.find((item) => item.id === selectedId) ?? next[0] ?? null);
  }, []);

  useEffect(() => {
    void load().catch((caught: unknown) =>
      setError(
        caught instanceof Error ? caught.message : "Unable to load events.",
      ),
    );
  }, [load]);
  useEffect(() => {
    let url: string | null = null;
    setBrandingUrl(null);
    if (selected?.has_branding)
      void downloadEventBranding(selected.id)
        .then((blob) => {
          url = URL.createObjectURL(blob);
          setBrandingUrl(url);
        })
        .catch(() => setBrandingUrl(null));
    return () => {
      if (url) URL.revokeObjectURL(url);
    };
  }, [selected?.has_branding, selected?.id]);

  async function action(work: () => Promise<ManagedEvent>, success: string) {
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      const updated = await work();
      await load(updated.id);
      setMessage(success);
      return updated;
    } catch (caught) {
      setError(
        caught instanceof Error ? caught.message : "Event operation failed.",
      );
      return null;
    } finally {
      setBusy(false);
    }
  }

  function create(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    void (async () => {
      const created = await action(
        () => createManagedEvent(eventPayload(data)),
        "Event created. Add its sub-events below.",
      );
      if (created) setCreating(false);
    })();
  }

  function updateEvent(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selected) return;
    const data = new FormData(event.currentTarget);
    void action(
      () => updateManagedEvent(selected.id, eventPayload(data, selected)),
      "Event parameters updated.",
    );
  }

  function addSubEvent(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selected) return;
    const data = new FormData(event.currentTarget);
    void action(
      () =>
        addManagedSubEvent(selected.id, {
          name: String(data.get("name")),
          description: String(data.get("description") || "") || null,
          starts_at: iso(data.get("starts_at")),
          ends_at: iso(data.get("ends_at")),
          location: String(data.get("location")),
          status: "draft",
          module_codes: [],
          capacity: Number(data.get("capacity")) || null,
        }),
      "Sub-event added.",
    );
  }

  function updateSubEvent(
    event: FormEvent<HTMLFormElement>,
    item: ManagedSubEvent,
  ) {
    event.preventDefault();
    if (!selected) return;
    const data = new FormData(event.currentTarget);
    void action(
      () =>
        updateManagedSubEvent(selected.id, item.id, {
          name: String(data.get("name")),
          description: String(data.get("description") || "") || null,
          starts_at: iso(data.get("starts_at")),
          ends_at: iso(data.get("ends_at")),
          location: String(data.get("location")),
          status: item.status,
          module_codes: item.module_codes,
          capacity: Number(data.get("capacity")) || null,
        }),
      "Sub-event parameters updated.",
    );
  }

  function removeSubEvent(item: ManagedSubEvent) {
    if (!selected) return;
    if (
      !window.confirm(
        `Delete “${item.name}” and all of its setup, calendar links, and operational data? This cannot be undone.`,
      )
    )
      return;
    void action(
      () => deleteManagedSubEvent(selected.id, item.id),
      "Sub-event permanently removed.",
    );
  }

  function cancelSelectedEvent() {
    if (!selected) return;
    const reason = window.prompt(
      `Why is “${selected.name}” being cancelled? This reason will be retained in the audit record.`,
    );
    if (reason === null) return;
    if (reason.trim().length < 3) {
      setError("Enter a cancellation reason of at least three characters.");
      return;
    }
    void action(
      () => cancelManagedEvent(selected.id, reason.trim()),
      "Event cancelled. Attendee access and calendar publishing are disabled.",
    );
  }

  function publishSelectedEvent() {
    if (!selected) return;
    if (
      !window.confirm(
        `Publish “${selected.name}”? Registered attendees will be able to enter when its scheduled event window opens.`,
      )
    )
      return;
    void action(
      () => publishManagedEvent(selected.id),
      "Event published. Attendee access will follow the scheduled event window.",
    );
  }

  function removeSelectedEvent() {
    if (!selected) return;
    const confirmation = window.prompt(
      `Permanent deletion cannot be undone. Type the event name to remove it:\n\n${selected.name}`,
    );
    if (confirmation !== selected.name) {
      if (confirmation !== null)
        setError("Event name did not match. Nothing was removed.");
      return;
    }
    const removedId = selected.id;
    setBusy(true);
    setError(null);
    setMessage(null);
    void deleteManagedEvent(removedId)
      .then(() => load())
      .then(() => setMessage("Event permanently removed."))
      .catch((caught: unknown) =>
        setError(
          caught instanceof Error
            ? caught.message
            : "Unable to remove the event.",
        ),
      )
      .finally(() => setBusy(false));
  }

  return (
    <div className="event-ui space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-2xl font-bold">Event management</h2>
          <p className="mt-2 text-slate-600">
            Create events, maintain dates and locations, and build the sub-event
            calendar.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Link
            className="rounded-xl border px-5 py-3 font-semibold"
            href="/events/archive"
          >
            Archived events
          </Link>
          <button
            className="rounded-xl bg-blue-800 px-5 py-3 font-semibold text-white"
            onClick={() => setCreating(true)}
            type="button"
          >
            + Create event
          </button>
        </div>
      </div>
      {message ? (
        <p className="rounded-xl bg-green-50 p-3 text-green-800">{message}</p>
      ) : null}
      {error ? (
        <p className="rounded-xl bg-red-50 p-3 text-red-800">{error}</p>
      ) : null}
      <div className="grid gap-5 xl:grid-cols-[280px_1fr]">
        <aside className="space-y-2">
          {events.map((item) => (
            <button
              className={`w-full rounded-xl border p-3 text-left ${selected?.id === item.id ? "selected-object" : "event-glass-pane"}`}
              key={item.id}
              onClick={() => {
                setSelected(item);
                setCreating(false);
              }}
              type="button"
            >
              <strong className="block">{item.name}</strong>
              <span className="text-xs uppercase">{item.status}</span>
            </button>
          ))}
        </aside>
        {creating || (!selected && !events.length) ? (
          <EventDetailsForm
            busy={busy}
            onSubmit={create}
            onCancel={events.length ? () => setCreating(false) : undefined}
          />
        ) : selected ? (
          <div className="space-y-5">
            <section className="event-glass-pane overflow-hidden rounded-2xl border">
              {brandingUrl ? (
                // Authenticated blob URL.
                // eslint-disable-next-line @next/next/no-img-element
                <img
                  alt="Event branding"
                  className="max-h-64 w-full object-cover"
                  src={brandingUrl}
                />
              ) : null}
              <div className="p-5">
                <h3 className="text-2xl font-bold">{selected.name}</h3>
                <label className="mt-3 inline-block cursor-pointer rounded-lg border px-3 py-2 font-semibold">
                  Upload branding image
                  <input
                    accept="image/png,image/jpeg,image/webp"
                    className="sr-only"
                    type="file"
                    onChange={(input) => {
                      const file = input.target.files?.[0];
                      if (file)
                        void action(
                          () => uploadEventBranding(selected.id, file),
                          "Branding updated.",
                        );
                    }}
                  />
                </label>
              </div>
            </section>
            <section className="event-glass-pane rounded-2xl border p-5">
              <p className="brand-eyebrow">Event setup</p>
              <h3 className="text-xl font-bold">Venue map</h3>
              <p className="mt-1 text-sm text-slate-300">
                Upload a visual venue overview for attendees. PDF and image
                files are displayed read-only; this does not alter booth layout.
              </p>
              <label className="mt-3 inline-block cursor-pointer rounded-lg border px-3 py-2 font-semibold">
                {selected.has_venue_map
                  ? "Replace venue map"
                  : "Upload venue map"}
                <input
                  accept="application/pdf,image/png,image/jpeg,image/webp,.pdf"
                  className="sr-only"
                  type="file"
                  onChange={(input) => {
                    const file = input.target.files?.[0];
                    if (file)
                      void action(
                        () => uploadEventVenueMap(selected.id, file),
                        "Venue map updated.",
                      );
                  }}
                />
              </label>
            </section>
            <EventDetailsForm
              busy={busy}
              event={selected}
              onSubmit={updateEvent}
            />
            <section className="event-glass-pane rounded-2xl border p-5">
              <p className="brand-eyebrow">Event activation</p>
              <h3 className="text-xl font-bold">Publication status</h3>
              <p className="mt-1 text-sm text-slate-400">
                Draft events remain available for admin, staff, and executive
                preview. Publishing opens attendee access during the scheduled
                event dates.
              </p>
              <div className="mt-4 flex flex-wrap items-center gap-3">
                <span className="rounded-full border px-3 py-2 text-sm font-bold uppercase">
                  {selected.status}
                </span>
                {selected.status === "draft" ? (
                  <button
                    className="rounded-xl bg-green-700 px-4 py-3 font-bold text-white"
                    disabled={busy}
                    onClick={publishSelectedEvent}
                    type="button"
                  >
                    Publish event
                  </button>
                ) : null}
              </div>
            </section>
            <section
              className="event-cancellation-panel rounded-2xl border border-red-300 bg-white p-5 text-red-950"
              style={{ backgroundColor: "#ffffff" }}
            >
              <p className="brand-eyebrow">Event lifecycle</p>
              <h3
                className="text-xl font-bold !text-red-700"
                style={{ color: "#b91c1c" }}
              >
                Cancellation and removal
              </h3>
              <p className="mt-1 text-sm !text-red-900">
                Cancellation preserves the event for audit history. Permanent
                removal deletes unreleased event data and cannot be undone.
              </p>
              {selected.status === "cancelled" ? (
                <div className="mt-3 rounded-xl border border-red-200 bg-white/70 p-3 text-sm">
                  <strong className="block">
                    {selected.cancellation_reason}
                  </strong>
                  <span>
                    Cancelled by{" "}
                    {selected.cancelled_by ?? "Unknown administrator"}
                    {selected.cancelled_at
                      ? ` on ${new Date(selected.cancelled_at).toLocaleString()}`
                      : ""}
                  </span>
                </div>
              ) : null}
              <div className="mt-4 flex flex-wrap gap-3">
                {selected.status !== "cancelled" &&
                selected.status !== "completed" ? (
                  <button
                    className="rounded-xl bg-amber-500 px-4 py-3 font-bold text-slate-950"
                    disabled={busy}
                    onClick={cancelSelectedEvent}
                    type="button"
                  >
                    Cancel event
                  </button>
                ) : null}
                {selected.status === "draft" ||
                selected.status === "cancelled" ? (
                  <button
                    className="rounded-xl bg-red-800 px-4 py-3 font-bold text-white"
                    disabled={busy}
                    onClick={removeSelectedEvent}
                    type="button"
                  >
                    Permanently remove event
                  </button>
                ) : null}
              </div>
            </section>
            <section className="event-glass-pane rounded-2xl border p-5">
              <p className="brand-eyebrow">Calendar</p>
              <h3 className="text-xl font-bold">Sub-events</h3>
              <div className="mt-4 space-y-3">
                {selected.sub_events.map((item) => (
                  <SubEventForm
                    busy={busy}
                    item={item}
                    key={item.id}
                    onSubmit={(event) => updateSubEvent(event, item)}
                    onDelete={() => removeSubEvent(item)}
                  />
                ))}
              </div>
              <div className="mt-5 border-t pt-5">
                <h4 className="font-bold">Add sub-event</h4>
                <SubEventForm busy={busy} onSubmit={addSubEvent} />
              </div>
            </section>
          </div>
        ) : null}
      </div>
    </div>
  );
}

function EventDetailsForm({
  event,
  busy,
  onSubmit,
  onCancel,
}: {
  event?: ManagedEvent;
  busy: boolean;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
  onCancel?: () => void;
}) {
  return (
    <form
      className="event-details-form event-glass-pane grid gap-4 rounded-2xl border p-5 sm:grid-cols-2"
      key={event ? `${event.id}-${event.starts_at}-${event.venue_name}` : "new"}
      onSubmit={onSubmit}
    >
      <div className="sm:col-span-2">
        <p className="brand-eyebrow">
          {event ? "Event parameters" : "New event"}
        </p>
        <h3 className="text-xl font-bold">
          {event ? "Edit event details" : "Create event"}
        </h3>
      </div>
      <Field defaultValue={event?.name} label="Event name" name="name" />
      <Field
        defaultValue={event?.slug}
        label="URL identifier"
        name="slug"
        pattern="[a-z0-9]+(?:-[a-z0-9]+)*"
      />
      <Field
        defaultValue={event?.timezone ?? "America/New_York"}
        label="Timezone"
        name="timezone"
      />
      <Field
        defaultValue={event ? localDateTime(event.starts_at) : undefined}
        label="Starts"
        name="starts_at"
        type="datetime-local"
      />
      <Field
        defaultValue={event ? localDateTime(event.ends_at) : undefined}
        label="Ends"
        name="ends_at"
        type="datetime-local"
      />
      <Field
        defaultValue={event?.venue_name}
        label="Venue name"
        name="venue_name"
      />
      <Field
        defaultValue={event?.address_line1}
        label="Street address"
        name="address_line1"
      />
      <Field
        defaultValue={event?.address_line2 ?? undefined}
        label="Address line 2"
        name="address_line2"
        required={false}
      />
      <Field defaultValue={event?.city} label="City" name="city" />
      <Field defaultValue={event?.state_code} label="State" name="state_code" />
      <Field
        defaultValue={event?.postal_code}
        label="Postal code"
        name="postal_code"
      />
      <Field
        defaultValue={event?.theme_primary_color ?? "#07142c"}
        label="Primary theme color"
        name="theme_primary_color"
        type="color"
      />
      <Field
        defaultValue={event?.theme_accent_color ?? "#ffd400"}
        label="Accent theme color"
        name="theme_accent_color"
        type="color"
      />
      <label className="text-sm font-semibold sm:col-span-2">
        Description
        <textarea
          className="mt-1 min-h-24 w-full rounded-lg border bg-white p-3"
          defaultValue={event?.description ?? ""}
          name="description"
        />
      </label>
      <div className="flex justify-end gap-3 sm:col-span-2">
        {onCancel ? (
          <button
            className="rounded-xl border px-5 py-3 font-semibold"
            onClick={onCancel}
            type="button"
          >
            Cancel
          </button>
        ) : null}
        <button
          className="rounded-xl bg-blue-800 px-5 py-3 font-semibold text-white"
          disabled={busy}
        >
          {event ? "Save event parameters" : "Create event"}
        </button>
      </div>
    </form>
  );
}

function SubEventForm({
  item,
  busy,
  onSubmit,
  onDelete,
}: {
  item?: ManagedSubEvent;
  busy: boolean;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
  onDelete?: () => void;
}) {
  return (
    <form
      className="event-sub-event-form event-glass-pane grid gap-2 rounded-xl border p-4 sm:grid-cols-2"
      key={item?.id ?? "new-sub-event"}
      onSubmit={onSubmit}
    >
      <Field defaultValue={item?.name} label="Name" name="name" />
      <Field defaultValue={item?.location} label="Location" name="location" />
      <Field
        defaultValue={item ? localDateTime(item.starts_at) : undefined}
        label="Starts"
        name="starts_at"
        type="datetime-local"
      />
      <Field
        defaultValue={item ? localDateTime(item.ends_at) : undefined}
        label="Ends"
        name="ends_at"
        type="datetime-local"
      />
      <Field
        defaultValue={item?.capacity?.toString()}
        label="Capacity"
        name="capacity"
        required={false}
        type="number"
      />
      <label className="text-sm font-semibold sm:col-span-2">
        Description
        <textarea
          className="mt-1 w-full rounded-lg border bg-white p-3"
          defaultValue={item?.description ?? ""}
          name="description"
        />
      </label>
      <div className="flex flex-wrap justify-end gap-2 sm:col-span-2">
        {item && onDelete ? (
          <button
            className="rounded-lg border border-red-300 px-4 py-3 font-semibold text-red-800"
            disabled={busy}
            onClick={onDelete}
            type="button"
          >
            Delete sub-event
          </button>
        ) : null}
        <button
          className="rounded-lg bg-blue-800 px-4 py-3 font-semibold text-white"
          disabled={busy}
        >
          {item ? "Save sub-event parameters" : "Add sub-event"}
        </button>
      </div>
    </form>
  );
}

function Field({
  label,
  required = true,
  type,
  ...props
}: {
  label: string;
  name: string;
  defaultValue?: string;
  type?: string;
  pattern?: string;
  required?: boolean;
}) {
  return (
    <label className="event-form-field text-sm font-semibold">
      {label}
      <input
        {...props}
        type={type}
        className={[
          "event-form-input mt-1 w-full rounded-lg border bg-white p-3",
          type === "date" || type === "datetime-local"
            ? "event-date-input"
            : "",
        ].join(" ")}
        required={required}
      />
    </label>
  );
}
