"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { listInternalMessages } from "@/lib/api";
import { useAuth } from "@/lib/auth";

export function MessageNotificationLink() {
  const { user } = useAuth();
  const [unread, setUnread] = useState(0);

  useEffect(() => {
    if (!user?.permissions.includes("communications.read")) return;
    let active = true;
    async function refresh() {
      try {
        const messages = await listInternalMessages();
        if (active) {
          setUnread(
            messages.filter(
              (message) =>
                message.recipient_email === user?.email && !message.read_at,
            ).length,
          );
        }
      } catch {
        // Notification polling must not interrupt the active workspace.
      }
    }
    void refresh();
    const timer = window.setInterval(() => void refresh(), 30_000);
    const onVisibility = () => {
      if (document.visibilityState === "visible") void refresh();
    };
    document.addEventListener("visibilitychange", onVisibility);
    return () => {
      active = false;
      window.clearInterval(timer);
      document.removeEventListener("visibilitychange", onVisibility);
    };
  }, [user]);

  if (!user?.permissions.includes("communications.read")) return null;

  return (
    <Link
      aria-label={`${unread} unread messages`}
      className="message-notification-link"
      href="/messages"
    >
      Messages
      {unread > 0 ? (
        <span className="message-notification-count">
          {unread > 99 ? "99+" : unread}
        </span>
      ) : null}
    </Link>
  );
}
