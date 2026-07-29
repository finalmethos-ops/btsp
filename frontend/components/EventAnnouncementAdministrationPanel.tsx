"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
import {
  AnnouncementAudience,
  createEventAnnouncement,
  deleteEventAnnouncement,
  EventAnnouncement,
  listEventAnnouncements,
  updateEventAnnouncement,
} from "@/lib/event-announcement-api";
import { ManagedEvent } from "@/lib/event-admin-api";

const audiences: Array<{ code: AnnouncementAudience; label: string }> = [
  { code: "staff", label: "Staff" },
  { code: "vendor", label: "Vendors" },
  { code: "franchise_representative", label: "Franchise representatives" },
  { code: "executive", label: "Executives" },
  { code: "admin", label: "Admins" },
];

const localDateTime = (value: string) => {
  const date = new Date(value);
  return new Date(date.getTime() - date.getTimezoneOffset() * 60_000)
    .toISOString()
    .slice(0, 16);
};

const nowLocal = () => localDateTime(new Date().toISOString());

const severityLabels = {
  info: "Informational",
  important: "Important",
  urgent: "Urgent",
};

export function EventAnnouncementAdministrationPanel({
  event,
}: {
  event: ManagedEvent;
}) {
  const [announcements, setAnnouncements] = useState<EventAnnouncement[]>([]);
  const [editing, setEditing] = useState<EventAnnouncement | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const load = useCallback(
    () => listEventAnnouncements(event.id).then(setAnnouncements),
    [event.id],
  );

  useEffect(() => {
    setEditing(null);
    void load();
  }, [load]);

  async function save(formEvent: FormEvent<HTMLFormElement>) {
    formEvent.preventDefault();
    const form = formEvent.currentTarget;
    const data = new FormData(form);
    const visibility = data.getAll(
      "visibility_categories",
    ) as AnnouncementAudience[];
    setBusy(true);
    setError(null);
    try {
      const expiresAt = String(data.get("expires_at") || "");
      const payload = {
        sub_event_id: String(data.get("sub_event_id") || "") || null,
        title: String(data.get("title")),
        body: String(data.get("body")),
        severity: String(data.get("severity")) as EventAnnouncement["severity"],
        visibility_categories: visibility,
        publishes_at: new Date(String(data.get("publishes_at"))).toISOString(),
        expires_at: expiresAt ? new Date(expiresAt).toISOString() : null,
        is_active: editing?.is_active ?? true,
      };
      if (editing) {
        await updateEventAnnouncement(event.id, editing.id, payload);
      } else {
        await createEventAnnouncement(event.id, payload);
      }
      form.reset();
      setEditing(null);
      await load();
    } catch (caught) {
      setError(
        caught instanceof Error
          ? caught.message
          : "Announcement could not be saved",
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="event-ui rounded-2xl border bg-white p-5">
      <p className="brand-eyebrow">Event communications</p>
      <h3 className="text-xl font-bold">Announcements and alerts</h3>
      <p className="mt-1 text-sm text-slate-600">
        Publish time-bounded messages to selected attendee categories, or target
        a specific sub-event audience.
      </p>
      {error ? (
        <p className="mt-3 rounded-lg bg-red-50 p-3 text-red-800">{error}</p>
      ) : null}
      <div className="mt-4 grid gap-5 lg:grid-cols-2">
        <form
          className="grid gap-3 rounded-xl bg-slate-50 p-4"
          key={editing?.id ?? "new-announcement"}
          onSubmit={save}
        >
          <label className="font-semibold">
            Target sub-event
            <select
              className="mt-1 w-full rounded-lg border bg-white p-3"
              defaultValue={editing?.sub_event_id ?? ""}
              name="sub_event_id"
            >
              <option value="">Entire event</option>
              {event.sub_events
                .filter((item) => item.status !== "cancelled")
                .map((item) => (
                  <option key={item.id} value={item.id}>
                    {item.name}
                  </option>
                ))}
            </select>
          </label>
          <input
            className="rounded-lg border bg-white p-3"
            defaultValue={editing?.title}
            name="title"
            placeholder="Announcement title"
            required
          />
          <textarea
            className="min-h-28 rounded-lg border bg-white p-3"
            defaultValue={editing?.body}
            name="body"
            placeholder="Message shown to eligible attendees"
            required
          />
          <label className="font-semibold">
            Severity
            <select
              className="mt-1 w-full rounded-lg border bg-white p-3"
              defaultValue={editing?.severity ?? "info"}
              name="severity"
            >
              <option value="info">Informational</option>
              <option value="important">Important</option>
              <option value="urgent">Urgent</option>
            </select>
          </label>
          <label className="font-semibold">
            Publish at
            <input
              className="mt-1 w-full rounded-lg border bg-white p-3"
              defaultValue={
                editing ? localDateTime(editing.publishes_at) : nowLocal()
              }
              name="publishes_at"
              required
              type="datetime-local"
            />
          </label>
          <label className="font-semibold">
            Expire at
            <input
              className="mt-1 w-full rounded-lg border bg-white p-3"
              defaultValue={
                editing?.expires_at
                  ? localDateTime(editing.expires_at)
                  : undefined
              }
              name="expires_at"
              type="datetime-local"
            />
          </label>
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
                ? "Save announcement"
                : "Publish announcement"}
          </button>
          {editing ? (
            <button
              className="rounded-xl border p-3 font-bold"
              onClick={() => setEditing(null)}
              type="button"
            >
              Cancel editing
            </button>
          ) : null}
        </form>
        <div className="max-h-[36rem] space-y-3 overflow-auto">
          {announcements.map((announcement) => (
            <article className="rounded-xl border p-4" key={announcement.id}>
              <div className="flex justify-between gap-3">
                <div>
                  <span className="text-xs font-bold uppercase text-blue-700">
                    {severityLabels[announcement.severity]}
                  </span>
                  <h4 className="font-bold">{announcement.title}</h4>
                  <p className="mt-1 text-sm text-slate-600">
                    {announcement.sub_event_name ?? "Entire event"} · Publishes{" "}
                    {new Date(announcement.publishes_at).toLocaleString()}
                  </p>
                </div>
                <div className="flex flex-col items-end gap-1">
                  <button
                    className="text-sm font-bold text-blue-700"
                    onClick={() => setEditing(announcement)}
                    type="button"
                  >
                    Edit
                  </button>
                  <button
                    className="text-sm font-bold text-amber-700"
                    onClick={() => {
                      setBusy(true);
                      void updateEventAnnouncement(event.id, announcement.id, {
                        sub_event_id: announcement.sub_event_id,
                        title: announcement.title,
                        body: announcement.body,
                        severity: announcement.severity,
                        visibility_categories:
                          announcement.visibility_categories,
                        publishes_at: announcement.publishes_at,
                        expires_at: announcement.expires_at,
                        is_active: !announcement.is_active,
                      })
                        .then(load)
                        .finally(() => setBusy(false));
                    }}
                    type="button"
                  >
                    {announcement.is_active ? "Hide" : "Publish"}
                  </button>
                  <button
                    className="text-sm font-bold text-red-700"
                    onClick={() => {
                      setBusy(true);
                      void deleteEventAnnouncement(event.id, announcement.id)
                        .then(load)
                        .finally(() => setBusy(false));
                    }}
                    type="button"
                  >
                    Remove
                  </button>
                </div>
              </div>
              <p className="mt-2 text-sm text-slate-600">{announcement.body}</p>
              <p className="mt-2 text-xs text-slate-500">
                {announcement.is_active ? "Active" : "Hidden"} · Visible:{" "}
                {announcement.visibility_categories
                  .map((item) => item.replaceAll("_", " "))
                  .join(", ")}
                {announcement.expires_at
                  ? ` · Expires ${new Date(announcement.expires_at).toLocaleString()}`
                  : ""}
              </p>
            </article>
          ))}
          {!announcements.length ? (
            <p className="rounded-xl border border-dashed p-5 text-slate-500">
              No announcements yet.
            </p>
          ) : null}
        </div>
      </div>
    </section>
  );
}
