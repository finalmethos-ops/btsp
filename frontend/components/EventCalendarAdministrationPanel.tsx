"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
import { ManagedEvent } from "@/lib/event-admin-api";
import {
  CalendarAudience,
  createEventCalendarEntry,
  deleteEventCalendarEntry,
  EventCalendarEntry,
  listEventCalendar,
  updateEventCalendarEntry,
} from "@/lib/event-calendar-api";

const localDateTime = (value: string) => {
  const date = new Date(value);
  return new Date(date.getTime() - date.getTimezoneOffset() * 60_000)
    .toISOString()
    .slice(0, 16);
};

const audiences: Array<{ code: CalendarAudience; label: string }> = [
  { code: "staff", label: "Staff" },
  { code: "vendor", label: "Vendors" },
  { code: "franchise_representative", label: "Franchise representatives" },
  { code: "executive", label: "Executives" },
  { code: "admin", label: "Admins" },
];

export function EventCalendarAdministrationPanel({
  event,
}: {
  event: ManagedEvent;
}) {
  const [entries, setEntries] = useState<EventCalendarEntry[]>([]);
  const [entryType, setEntryType] = useState<"text" | "sub_event">("text");
  const [editing, setEditing] = useState<EventCalendarEntry | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const load = useCallback(
    () => listEventCalendar(event.id).then(setEntries),
    [event.id],
  );
  useEffect(() => {
    void load();
  }, [load]);

  async function create(formEvent: FormEvent<HTMLFormElement>) {
    formEvent.preventDefault();
    const form = formEvent.currentTarget;
    const data = new FormData(form);
    const subEvent = event.sub_events.find(
      (item) => item.id === data.get("sub_event_id"),
    );
    const visibility = data.getAll(
      "visibility_categories",
    ) as CalendarAudience[];
    setBusy(true);
    setError(null);
    try {
      const payload = {
        entry_type: entryType,
        sub_event_id: entryType === "sub_event" ? (subEvent?.id ?? null) : null,
        title:
          entryType === "sub_event"
            ? (subEvent?.name ?? "Sub-event")
            : String(data.get("title")),
        description:
          entryType === "sub_event"
            ? (subEvent?.description ?? null)
            : String(data.get("description") || "") || null,
        starts_at:
          entryType === "sub_event"
            ? (subEvent?.starts_at ?? "")
            : new Date(String(data.get("starts_at"))).toISOString(),
        ends_at:
          entryType === "sub_event"
            ? (subEvent?.ends_at ?? "")
            : new Date(String(data.get("ends_at"))).toISOString(),
        location:
          entryType === "sub_event"
            ? (subEvent?.location ?? null)
            : String(data.get("location") || "") || null,
        visibility_categories: visibility,
        is_active: editing?.is_active ?? true,
      };
      if (editing) {
        await updateEventCalendarEntry(event.id, editing.id, payload);
      } else {
        await createEventCalendarEntry(event.id, payload);
      }
      form.reset();
      setEntryType("text");
      setEditing(null);
      await load();
    } catch (caught) {
      setError(
        caught instanceof Error
          ? caught.message
          : "Unable to create the calendar entry.",
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="event-ui rounded-2xl border bg-white p-5">
      <p className="brand-eyebrow">Show planning</p>
      <h3 className="text-xl font-bold">Dynamic event calendar</h3>
      <p className="mt-1 text-sm text-slate-600">
        Publish informational schedule items or link active sub-events, then
        choose the attendee categories that can see them.
      </p>
      {error ? (
        <p className="mt-3 rounded-lg bg-red-50 p-3 text-red-800">{error}</p>
      ) : null}
      <div className="mt-4 grid gap-5 lg:grid-cols-2">
        <form
          className="grid gap-3 rounded-xl bg-slate-50 p-4"
          key={editing?.id ?? "new-calendar-entry"}
          onSubmit={create}
        >
          <label className="font-semibold">
            Calendar item type
            <select
              className="mt-1 w-full rounded-lg border bg-white p-3"
              name="entry_type"
              onChange={(input) =>
                setEntryType(input.target.value as "text" | "sub_event")
              }
              value={entryType}
            >
              <option value="text">Text-only calendar item</option>
              <option value="sub_event">Active sub-event</option>
            </select>
          </label>
          {entryType === "sub_event" ? (
            <label className="font-semibold">
              Sub-event
              <select
                className="mt-1 w-full rounded-lg border bg-white p-3"
                name="sub_event_id"
                defaultValue={editing?.sub_event_id ?? undefined}
                required
              >
                {event.sub_events
                  .filter((item) => item.status !== "cancelled")
                  .map((item) => (
                    <option key={item.id} value={item.id}>
                      {item.name}
                    </option>
                  ))}
              </select>
            </label>
          ) : (
            <>
              <input
                className="rounded-lg border bg-white p-3"
                name="title"
                placeholder="Calendar title"
                defaultValue={editing?.title}
                required
              />
              <textarea
                className="rounded-lg border bg-white p-3"
                name="description"
                placeholder="Details or instructions"
                defaultValue={editing?.description ?? ""}
              />
              <input
                className="rounded-lg border bg-white p-3"
                name="location"
                placeholder="Location (optional)"
                defaultValue={editing?.location ?? ""}
              />
              <label className="font-semibold">
                Starts
                <input
                  className="mt-1 w-full rounded-lg border bg-white p-3"
                  name="starts_at"
                  defaultValue={
                    editing ? localDateTime(editing.starts_at) : undefined
                  }
                  required
                  type="datetime-local"
                />
              </label>
              <label className="font-semibold">
                Ends
                <input
                  className="mt-1 w-full rounded-lg border bg-white p-3"
                  name="ends_at"
                  defaultValue={
                    editing ? localDateTime(editing.ends_at) : undefined
                  }
                  required
                  type="datetime-local"
                />
              </label>
            </>
          )}
          <fieldset className="rounded-lg border bg-white p-3">
            <legend className="px-1 text-sm font-bold">Visible to</legend>
            {audiences.map((audience) => (
              <label
                className="mt-1 flex items-center gap-2 text-sm"
                key={audience.code}
              >
                <input
                  defaultChecked={
                    editing
                      ? editing.visibility_categories.includes(audience.code)
                      : true
                  }
                  name="visibility_categories"
                  type="checkbox"
                  value={audience.code}
                />
                {audience.label}
              </label>
            ))}
          </fieldset>
          <button
            className="rounded-xl bg-blue-800 p-3 font-bold text-white disabled:bg-slate-400"
            disabled={busy}
          >
            {busy
              ? "Saving…"
              : editing
                ? "Save calendar item"
                : "Add to show calendar"}
          </button>
          {editing ? (
            <button
              className="rounded-xl border p-3 font-bold"
              onClick={() => {
                setEditing(null);
                setEntryType("text");
              }}
              type="button"
            >
              Cancel editing
            </button>
          ) : null}
        </form>
        <div className="max-h-[36rem] space-y-3 overflow-auto">
          {entries.map((entry) => (
            <article className="rounded-xl border p-4" key={entry.id}>
              <div className="flex justify-between gap-3">
                <div>
                  <span className="text-xs font-bold uppercase text-blue-700">
                    {entry.entry_type.replace("_", " ")}
                  </span>
                  <h4 className="font-bold">{entry.title}</h4>
                  <p className="text-sm text-slate-600">
                    {new Date(entry.starts_at).toLocaleString()} ·{" "}
                    {entry.location ?? "Location TBA"}
                  </p>
                </div>
                <div className="flex flex-col items-end gap-1">
                  <button
                    className="text-sm font-bold text-blue-700"
                    onClick={() => {
                      setEditing(entry);
                      setEntryType(entry.entry_type);
                    }}
                    type="button"
                  >
                    Edit
                  </button>
                  <button
                    className="text-sm font-bold text-amber-700"
                    onClick={() => {
                      setBusy(true);
                      void updateEventCalendarEntry(event.id, entry.id, {
                        entry_type: entry.entry_type,
                        sub_event_id: entry.sub_event_id,
                        title: entry.title,
                        description: entry.description,
                        starts_at: entry.starts_at,
                        ends_at: entry.ends_at,
                        location: entry.location,
                        visibility_categories: entry.visibility_categories,
                        is_active: !entry.is_active,
                      })
                        .then(load)
                        .finally(() => setBusy(false));
                    }}
                    type="button"
                  >
                    {entry.is_active ? "Hide" : "Publish"}
                  </button>
                  <button
                    className="text-sm font-bold text-red-700"
                    onClick={() => {
                      if (
                        !window.confirm(
                          `Remove “${entry.title}” from the event calendar?`,
                        )
                      )
                        return;
                      setBusy(true);
                      setError(null);
                      void deleteEventCalendarEntry(event.id, entry.id)
                        .then(load)
                        .catch((caught: unknown) =>
                          setError(
                            caught instanceof Error
                              ? caught.message
                              : "Unable to remove the calendar item.",
                          ),
                        )
                        .finally(() => setBusy(false));
                    }}
                    type="button"
                  >
                    Remove
                  </button>
                </div>
              </div>
              <p className="mt-2 text-xs text-slate-500">
                {entry.is_active ? "Published" : "Hidden"} · Visible:{" "}
                {entry.visibility_categories
                  .map((item) => item.replaceAll("_", " "))
                  .join(", ")}
              </p>
            </article>
          ))}
          {!entries.length ? (
            <p className="rounded-xl border border-dashed p-5 text-slate-500">
              No calendar items yet.
            </p>
          ) : null}
        </div>
      </div>
    </section>
  );
}
