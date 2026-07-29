"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { listInternalMessages } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { listMyEventAnnouncements } from "@/lib/event-announcement-api";
import { listNotificationHistory } from "@/lib/notification-history-api";

const enabledKey = "btsp.event-alerts.enabled";
const seenKey = "btsp.event-alerts.seen";

type SeenAlerts = {
  announcements: string[];
  messages: number[];
  notifications: number[];
};

function readSeen(): SeenAlerts {
  try {
    const parsed = JSON.parse(
      localStorage.getItem(seenKey) ?? "{}",
    ) as Partial<SeenAlerts>;
    return {
      announcements: parsed.announcements ?? [],
      messages: parsed.messages ?? [],
      notifications: parsed.notifications ?? [],
    };
  } catch {
    return { announcements: [], messages: [], notifications: [] };
  }
}

function saveSeen(seen: SeenAlerts) {
  localStorage.setItem(
    seenKey,
    JSON.stringify({
      announcements: seen.announcements.slice(-250),
      messages: seen.messages.slice(-250),
      notifications: seen.notifications.slice(-250),
    }),
  );
}

function showNotification(title: string, body: string, href: string) {
  const notification = new Notification(title, {
    body,
    icon: "/brand/buddys-logo-compact.png",
    tag: `btsp-${href}-${title}`,
  });
  notification.onclick = () => {
    window.focus();
    window.location.assign(href);
    notification.close();
  };
}

export function EventNotificationControl() {
  const { user } = useAuth();
  const supported = typeof window !== "undefined" && "Notification" in window;
  const [enabled, setEnabled] = useState(false);
  const [busy, setBusy] = useState(false);
  const initialized = useRef(false);

  useEffect(() => {
    if (!supported) return;
    setEnabled(
      Notification.permission === "granted" &&
        localStorage.getItem(enabledKey) === "true",
    );
  }, [supported]);

  const checkAlerts = useCallback(async () => {
    if (!enabled || Notification.permission !== "granted" || !user) return;
    const [announcements, messages, notifications] = await Promise.all([
      listMyEventAnnouncements().catch(() => []),
      listInternalMessages().catch(() => []),
      listNotificationHistory().catch(() => []),
    ]);
    const urgent = announcements.filter(
      (item) => item.severity === "urgent" || item.severity === "important",
    );
    const unread = messages.filter(
      (item) => item.recipient_email === user.email && !item.read_at,
    );
    const eventTaskAlerts = notifications.filter(
      (item) =>
        item.workflow_code === "EVENTS" &&
        item.entity_type === "event_staff_task",
    );
    const seen = readSeen();
    if (initialized.current) {
      urgent
        .filter((item) => !seen.announcements.includes(item.id))
        .forEach((item) =>
          showNotification(item.title, item.body, "/events/calendar"),
        );
      unread
        .filter((item) => !seen.messages.includes(item.id))
        .forEach((item) =>
          showNotification("New event message", item.subject, "/messages"),
        );
      eventTaskAlerts
        .filter((item) => !seen.notifications.includes(item.notification_id))
        .forEach((item) =>
          showNotification(
            item.subject,
            item.body,
            item.action_href ?? "/events/calendar",
          ),
        );
    }
    saveSeen({
      announcements: [
        ...new Set([...seen.announcements, ...urgent.map((item) => item.id)]),
      ],
      messages: [
        ...new Set([...seen.messages, ...unread.map((item) => item.id)]),
      ],
      notifications: [
        ...new Set([
          ...seen.notifications,
          ...eventTaskAlerts.map((item) => item.notification_id),
        ]),
      ],
    });
    initialized.current = true;
  }, [enabled, user]);

  useEffect(() => {
    void checkAlerts();
    if (!enabled) return;
    const timer = window.setInterval(() => void checkAlerts(), 30_000);
    const onVisibility = () => {
      if (document.visibilityState === "visible") void checkAlerts();
    };
    document.addEventListener("visibilitychange", onVisibility);
    return () => {
      window.clearInterval(timer);
      document.removeEventListener("visibilitychange", onVisibility);
    };
  }, [checkAlerts, enabled]);

  async function toggle() {
    if (!supported) return;
    if (enabled) {
      localStorage.setItem(enabledKey, "false");
      setEnabled(false);
      initialized.current = false;
      return;
    }
    setBusy(true);
    try {
      const permission = await Notification.requestPermission();
      const next = permission === "granted";
      localStorage.setItem(enabledKey, String(next));
      initialized.current = false;
      setEnabled(next);
    } finally {
      setBusy(false);
    }
  }

  if (!supported) return null;

  return (
    <button
      aria-pressed={enabled}
      className={`event-alert-toggle ${enabled ? "is-active" : ""}`}
      disabled={busy}
      onClick={() => void toggle()}
      title="Receive important event announcements and message alerts while BTSP is open"
      type="button"
    >
      {busy ? "Alerts…" : enabled ? "Alerts on" : "Enable alerts"}
    </button>
  );
}
