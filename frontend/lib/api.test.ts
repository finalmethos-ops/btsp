import { afterEach, describe, expect, it, vi } from "vitest";
import {
  apiDownload,
  apiDownloadWithFilename,
  apiFetch,
  clearToken,
  getStoredToken,
  storeToken,
} from "./api";

class MemoryStorage {
  private values = new Map<string, string>();
  getItem(key: string) {
    return this.values.get(key) ?? null;
  }
  setItem(key: string, value: string) {
    this.values.set(key, value);
  }
  removeItem(key: string) {
    this.values.delete(key);
  }
}

function jsonResponse(status: number, payload: unknown) {
  return {
    headers: new Headers({ "content-type": "application/json" }),
    json: async () => payload,
    ok: false,
    status,
  } as Response;
}

function textResponse(status: number, body: string) {
  return {
    headers: new Headers({ "content-type": "text/plain" }),
    ok: false,
    status,
    text: async () => body,
  } as Response;
}

function downloadResponse(contentDisposition: string) {
  const blob = new Blob(["report"]);
  return {
    blob: async () => blob,
    headers: new Headers({ "content-disposition": contentDisposition }),
    ok: true,
    status: 200,
  } as Response;
}

afterEach(() => vi.unstubAllGlobals());

describe("BTSP API error handling", () => {
  it("surfaces FastAPI detail messages from JSON responses", async () => {
    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockResolvedValue(
          jsonResponse(422, { detail: "Slide image is required" }),
        ),
    );

    await expect(
      apiFetch("/event-product-slides", { method: "POST" }),
    ).rejects.toThrow("Slide image is required");
  });

  it("formats FastAPI validation arrays into readable field messages", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        jsonResponse(422, {
          detail: [
            {
              loc: ["body", "event_unit_cost"],
              msg: "Input should be greater than or equal to 0",
            },
          ],
        }),
      ),
    );

    await expect(
      apiFetch("/event-product-slides", { method: "POST" }),
    ).rejects.toThrow(
      "event_unit_cost: Input should be greater than or equal to 0",
    );
  });

  it("surfaces text download errors instead of only status codes", async () => {
    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockResolvedValue(
          textResponse(500, "Floor plan preview was not found"),
        ),
    );

    await expect(
      apiDownload("/vendor-hall/events/event-1/floor-map/content"),
    ).rejects.toThrow("Floor plan preview was not found");
  });

  it("returns safe filenames from download content-disposition headers", async () => {
    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockResolvedValue(
          downloadResponse('attachment; filename="Vendor Hall: Summary.csv"'),
        ),
    );

    await expect(
      apiDownloadWithFilename("/vendor-hall/report"),
    ).resolves.toMatchObject({
      filename: "Vendor Hall- Summary.csv",
    });
  });

  it("decodes RFC 5987 download filenames and strips path separators", async () => {
    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockResolvedValue(
          downloadResponse(
            "attachment; filename*=UTF-8''Event%20Orders%2FBackup.xlsx",
          ),
        ),
    );

    await expect(
      apiDownloadWithFilename("/event-order-review/report"),
    ).resolves.toMatchObject({
      filename: "Event Orders-Backup.xlsx",
    });
  });
});

describe("BTSP session token storage", () => {
  it("stores tokens only for the browser session and removes legacy copies", () => {
    const localStorage = new MemoryStorage();
    const sessionStorage = new MemoryStorage();
    vi.stubGlobal("window", { localStorage, sessionStorage });

    localStorage.setItem("btsp.access_token", "legacy-token");
    expect(getStoredToken()).toBe("legacy-token");
    expect(localStorage.getItem("btsp.access_token")).toBeNull();
    expect(sessionStorage.getItem("btsp.access_token")).toBe("legacy-token");

    storeToken("session-token");
    expect(sessionStorage.getItem("btsp.access_token")).toBe("session-token");
    expect(localStorage.getItem("btsp.access_token")).toBeNull();

    clearToken();
    expect(sessionStorage.getItem("btsp.access_token")).toBeNull();
  });
});
