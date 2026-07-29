"use client";

import { useEffect, useRef, useState } from "react";
import { useOnlineStatus } from "@/lib/use-online-status";

export function EventConnectivityStatus() {
  const online = useOnlineStatus();
  const wasOffline = useRef(false);
  const [restored, setRestored] = useState(false);

  useEffect(() => {
    document.body.classList.toggle("event-network-offline", !online);
    if (!online) {
      wasOffline.current = true;
      setRestored(false);
      return;
    }
    if (wasOffline.current) {
      setRestored(true);
      const timer = window.setTimeout(() => setRestored(false), 15_000);
      return () => window.clearTimeout(timer);
    }
  }, [online]);

  useEffect(
    () => () => document.body.classList.remove("event-network-offline"),
    [],
  );

  if (online && !restored) return null;
  return (
    <aside
      className={`event-connectivity-status ${online ? "is-restored" : "is-offline"}`}
      role="status"
    >
      <div>
        <strong>{online ? "Connection restored" : "You are offline"}</strong>
        <span>
          {online
            ? "Refresh when ready to synchronize current event information."
            : "Cached schedules, passes, maps, and routes remain available. Updates are paused."}
        </span>
      </div>
      {online ? (
        <button onClick={() => window.location.reload()} type="button">
          Refresh event data
        </button>
      ) : null}
    </aside>
  );
}
