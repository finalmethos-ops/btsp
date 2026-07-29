import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { subscribeEventRealtime } from "./event-realtime";

vi.mock("./api", () => ({
  getStoredToken: () => "test-token",
}));

vi.mock("./api-origin", () => ({
  getApiBaseUrl: () => "https://btsp.example.test",
}));

class MockWebSocket {
  static instances: MockWebSocket[] = [];
  static throwOnCreate = false;

  onclose: (() => void) | null = null;
  onerror: (() => void) | null = null;
  onmessage: (() => void) | null = null;
  onopen: (() => void) | null = null;
  send = vi.fn();
  close = vi.fn(() => this.onclose?.());

  constructor(
    public readonly url: string,
    public readonly protocols: string[],
  ) {
    if (MockWebSocket.throwOnCreate) {
      throw new Error("socket unavailable");
    }
    MockWebSocket.instances.push(this);
  }
}

describe("event realtime subscription", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    MockWebSocket.instances = [];
    MockWebSocket.throwOnCreate = false;
    vi.stubGlobal("WebSocket", MockWebSocket);
    vi.stubGlobal("window", {
      clearInterval,
      clearTimeout,
      location: { origin: "https://app.example.test" },
      setInterval,
      setTimeout,
    });
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.unstubAllGlobals();
  });

  it("retries when the browser cannot create the websocket immediately", () => {
    MockWebSocket.throwOnCreate = true;
    const unsubscribe = subscribeEventRealtime("sub-1", vi.fn());

    expect(MockWebSocket.instances).toHaveLength(0);
    MockWebSocket.throwOnCreate = false;
    vi.advanceTimersByTime(2_000);

    expect(MockWebSocket.instances).toHaveLength(1);
    expect(String(MockWebSocket.instances[0].url)).toBe(
      "wss://btsp.example.test/api/v1/event-realtime/sub-1",
    );
    expect(MockWebSocket.instances[0].protocols).toEqual([
      "btsp-token.test-token",
    ]);
    unsubscribe();
  });

  it("keeps the polling callback alive and reconnects after heartbeat failures", () => {
    const onEvent = vi.fn();
    const unsubscribe = subscribeEventRealtime("sub-2", onEvent);
    const first = MockWebSocket.instances[0];
    first.onopen?.();
    first.onmessage?.();
    first.send.mockImplementationOnce(() => {
      throw new Error("network dropped");
    });

    vi.advanceTimersByTime(20_000);
    expect(first.close).toHaveBeenCalled();
    expect(onEvent).toHaveBeenCalledTimes(1);

    vi.advanceTimersByTime(2_000);
    expect(MockWebSocket.instances).toHaveLength(2);
    unsubscribe();
  });
});
