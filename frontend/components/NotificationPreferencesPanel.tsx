"use client";

import { FormEvent, useEffect, useState } from "react";
import {
  getNotificationPreferences,
  NotificationPreferences,
  saveNotificationPreferences,
} from "@/lib/notification-preferences-api";

export function NotificationPreferencesPanel() {
  const [preferences, setPreferences] =
    useState<NotificationPreferences | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  useEffect(() => {
    void getNotificationPreferences().then(setPreferences);
  }, []);
  if (!preferences)
    return (
      <p className="text-sm text-slate-500">
        Loading notification preferences…
      </p>
    );
  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    const updated = await saveNotificationPreferences({
      in_app_enabled: data.get("in_app_enabled") === "on",
      email_enabled: data.get("email_enabled") === "on",
      quiet_hours_start: String(data.get("quiet_hours_start") || "") || null,
      quiet_hours_end: String(data.get("quiet_hours_end") || "") || null,
    });
    setPreferences(updated);
    setMessage("Notification preferences saved.");
  }
  return (
    <form
      className="event-glass-pane grid gap-3 rounded-2xl border p-5"
      onSubmit={(event) => void save(event)}
    >
      <p className="brand-eyebrow">Notification settings</p>
      <h2 className="text-xl font-bold">Reminder preferences</h2>
      <label className="flex gap-2">
        <input
          defaultChecked={preferences.in_app_enabled}
          name="in_app_enabled"
          type="checkbox"
        />{" "}
        In-app reminders
      </label>
      <label className="flex gap-2">
        <input
          defaultChecked={preferences.email_enabled}
          name="email_enabled"
          type="checkbox"
        />{" "}
        Email reminders
      </label>
      <div className="grid gap-3 sm:grid-cols-2">
        <label>
          Quiet hours start
          <input
            className="mt-1 w-full rounded-lg border p-2"
            defaultValue={preferences.quiet_hours_start ?? ""}
            name="quiet_hours_start"
            placeholder="22:00"
          />
        </label>
        <label>
          Quiet hours end
          <input
            className="mt-1 w-full rounded-lg border p-2"
            defaultValue={preferences.quiet_hours_end ?? ""}
            name="quiet_hours_end"
            placeholder="07:00"
          />
        </label>
      </div>
      <button className="brand-button" type="submit">
        Save preferences
      </button>
      {message ? <p className="text-sm text-green-700">{message}</p> : null}
    </form>
  );
}
