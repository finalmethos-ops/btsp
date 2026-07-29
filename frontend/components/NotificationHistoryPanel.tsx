"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  listNotificationHistory,
  NotificationEvent,
  retryNotification,
} from "@/lib/notification-history-api";
import { useAuth } from "@/lib/auth";

export function NotificationHistoryPanel() {
  const [events, setEvents] = useState<NotificationEvent[]>([]);
  const [statusFilter, setStatusFilter] = useState("all");
  const { user } = useAuth();
  useEffect(() => {
    let active = true;
    const refresh = () =>
      void listNotificationHistory()
        .then((items) => {
          if (active) setEvents(items);
        })
        .catch(() => undefined);
    refresh();
    const timer = window.setInterval(refresh, 30_000);
    return () => {
      active = false;
      window.clearInterval(timer);
    };
  }, []);
  const canRetry = user?.permissions.includes("notifications.manage");
  const visibleEvents =
    statusFilter === "all"
      ? events
      : events.filter((event) => event.status === statusFilter);
  return (
    <section className="event-glass-pane rounded-2xl border p-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="brand-eyebrow">Notification audit</p>
          <h1 className="text-2xl font-bold">Delivery history</h1>
          <p className="mt-1 text-sm text-slate-400">
            Recent reminders and system notifications for your account.
          </p>
        </div>
        <Link
          className="rounded-lg border px-3 py-2 text-sm font-bold"
          href="/notification-preferences"
        >
          Preferences
        </Link>
      </div>
      <div className="mt-4 grid gap-2 sm:grid-cols-4">
        {["queued", "sent", "failed", "skipped"].map((status) => (
          <button
            className="rounded-lg border p-2 text-left"
            key={status}
            onClick={() => setStatusFilter(status)}
            type="button"
          >
            <span className="block text-xs uppercase text-slate-400">
              {status}
            </span>
            <strong>
              {events.filter((event) => event.status === status).length}
            </strong>
          </button>
        ))}
      </div>
      <select
        className="mt-4 rounded-lg border p-2"
        onChange={(event) => setStatusFilter(event.target.value)}
        value={statusFilter}
      >
        <option value="all">All statuses</option>
        <option value="queued">Queued</option>
        <option value="sent">Sent</option>
        <option value="failed">Failed</option>
        <option value="skipped">Skipped</option>
      </select>
      <div className="mt-4 space-y-2">
        {visibleEvents.map((event) => (
          <article
            className="rounded-xl border border-white/10 p-3"
            key={event.notification_id}
          >
            <div className="flex flex-wrap justify-between gap-2">
              <strong>{event.subject}</strong>
              <span className="text-xs uppercase text-slate-400">
                {event.status}
              </span>
            </div>
            <p className="mt-1 text-sm text-slate-300">{event.body}</p>
            <p className="mt-1 text-xs text-slate-500">
              {new Date(event.created_at).toLocaleString()} · {event.channel}
            </p>
            {event.action_href ? (
              <Link
                className="mt-2 inline-flex rounded-lg border px-3 py-1 text-xs font-bold"
                href={event.action_href}
              >
                Open related workspace
              </Link>
            ) : null}
            {canRetry && event.status === "failed" ? (
              <button
                className="mt-2 rounded-lg border px-3 py-1 text-xs font-bold"
                onClick={() =>
                  void retryNotification(event.notification_id).then(
                    (updated) =>
                      setEvents((items) =>
                        items.map((item) =>
                          item.notification_id === updated.notification_id
                            ? updated
                            : item,
                        ),
                      ),
                  )
                }
                type="button"
              >
                Retry delivery
              </button>
            ) : null}
          </article>
        ))}
        {!visibleEvents.length ? (
          <p className="rounded-xl border border-dashed p-4 text-sm text-slate-500">
            No notifications match this filter.
          </p>
        ) : null}
      </div>
    </section>
  );
}
