import { getStoredToken } from "./api";
import { getApiBaseUrl } from "./api-origin";

type EventRealtimeScope = "user" | "projector" | "presenter";

function subscribeScopedEventRealtime(
  subEventId: string,
  scope: EventRealtimeScope,
  accessToken: () => string | null,
  onEvent: () => void,
): () => void {
  let socket: WebSocket | null = null;
  let reconnect: number | null = null;
  let heartbeat: number | null = null;
  let reconnectDelay = 2_000;
  let stopped = false;

  const clearHeartbeat = () => {
    if (heartbeat) window.clearInterval(heartbeat);
    heartbeat = null;
  };

  const scheduleReconnect = () => {
    if (stopped || reconnect) return;
    reconnect = window.setTimeout(() => {
      reconnect = null;
      reconnectDelay = Math.min(reconnectDelay * 1.6, 30_000);
      connect();
    }, reconnectDelay);
  };

  const connect = () => {
    if (typeof window === "undefined" || typeof WebSocket === "undefined")
      return;
    const token = accessToken();
    if (!token || stopped) return;
    const origin = getApiBaseUrl() || window.location.origin;
    const url = new URL(`/api/v1/event-realtime/${subEventId}`, origin);
    url.protocol = url.protocol === "https:" ? "wss:" : "ws:";
    try {
      const protocolPrefix =
        scope === "user"
          ? "btsp-token"
          : scope === "projector"
            ? "btsp-projector"
            : "btsp-presenter";
      socket = new WebSocket(url, [`${protocolPrefix}.${token}`]);
    } catch {
      scheduleReconnect();
      return;
    }
    socket.onmessage = () => onEvent();
    socket.onopen = () => {
      reconnectDelay = 2_000;
      clearHeartbeat();
      heartbeat = window.setInterval(() => {
        try {
          socket?.send("ping");
        } catch {
          socket?.close();
        }
      }, 20_000);
    };
    socket.onclose = () => {
      clearHeartbeat();
      socket = null;
      scheduleReconnect();
    };
    socket.onerror = () => {
      socket?.close();
    };
  };
  connect();
  return () => {
    stopped = true;
    if (reconnect) window.clearTimeout(reconnect);
    reconnect = null;
    clearHeartbeat();
    socket?.close();
    socket = null;
  };
}

export function subscribeEventRealtime(
  subEventId: string,
  onEvent: () => void,
): () => void {
  return subscribeScopedEventRealtime(
    subEventId,
    "user",
    getStoredToken,
    onEvent,
  );
}

export function subscribeProjectorRealtime(
  subEventId: string,
  projectorToken: string,
  onEvent: () => void,
): () => void {
  return subscribeScopedEventRealtime(
    subEventId,
    "projector",
    () => projectorToken,
    onEvent,
  );
}

export function subscribePresenterRealtime(
  subEventId: string,
  presenterToken: string,
  onEvent: () => void,
): () => void {
  return subscribeScopedEventRealtime(
    subEventId,
    "presenter",
    () => presenterToken,
    onEvent,
  );
}
