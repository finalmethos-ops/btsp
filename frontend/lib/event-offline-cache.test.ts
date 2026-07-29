import { beforeEach, describe, expect, it } from "vitest";
import {
  cacheEventData,
  clearEventOfflineCache,
  readCachedEventData,
} from "./event-offline-cache";

class MemoryStorage {
  private values = new Map<string, string>();
  get length() {
    return this.values.size;
  }
  key(index: number) {
    return [...this.values.keys()][index] ?? null;
  }
  getItem(key: string) {
    return this.values.get(key) ?? null;
  }
  setItem(key: string, value: string) {
    this.values.set(key, value);
  }
  removeItem(key: string) {
    this.values.delete(key);
  }
  clear() {
    this.values.clear();
  }
}

describe("event offline session cache", () => {
  beforeEach(() => {
    Object.defineProperty(globalThis, "sessionStorage", {
      configurable: true,
      value: new MemoryStorage(),
    });
  });

  it("returns event data only before its access expiration", () => {
    cacheEventData(
      "schedule",
      { title: "Live buying" },
      "2999-01-01T00:00:00Z",
    );
    expect(readCachedEventData("schedule")).toEqual({ title: "Live buying" });

    cacheEventData("expired", { title: "Old show" }, "2000-01-01T00:00:00Z");
    expect(readCachedEventData("expired")).toBeNull();
  });

  it("clears all event snapshots on sign-out", () => {
    cacheEventData("schedule", [1], "2999-01-01T00:00:00Z");
    sessionStorage.setItem("unrelated", "keep");
    clearEventOfflineCache();
    expect(readCachedEventData("schedule")).toBeNull();
    expect(sessionStorage.getItem("unrelated")).toBe("keep");
  });
});
