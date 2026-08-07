import { afterEach, describe, expect, it, vi } from "vitest";
import {
  apiDownload,
  apiDownloadWithFilename,
  apiFetch,
  clearToken,
  getStoredToken,
  storeRefreshToken,
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

function htmlResponse(status: number, body: string) {
  return new Response(body, {
    status,
    headers: { "content-type": "text/html; charset=UTF-8" },
  });
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
  it("coalesces concurrent identical reads without retaining stale data", async () => {
    let resolveResponse: ((response: Response) => void) | undefined;
    const fetchMock = vi.fn(
      () =>
        new Promise<Response>((resolve) => {
          resolveResponse = resolve;
        }),
    );
    vi.stubGlobal("fetch", fetchMock);

    const first = apiFetch<{ value: number }>("/events/mine");
    const second = apiFetch<{ value: number }>("/events/mine");
    expect(fetchMock).toHaveBeenCalledTimes(1);
    resolveResponse?.(
      new Response(JSON.stringify({ value: 1 }), {
        status: 200,
        headers: { "content-type": "application/json" },
      }),
    );
    await expect(Promise.all([first, second])).resolves.toEqual([
      { value: 1 },
      { value: 1 },
    ]);

    vi.mocked(fetch).mockResolvedValueOnce(
      new Response(JSON.stringify({ value: 2 }), {
        status: 200,
        headers: { "content-type": "application/json" },
      }),
    );
    await expect(apiFetch<{ value: number }>("/events/mine")).resolves.toEqual({
      value: 2,
    });
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });

  it("shares one refresh operation across concurrent expired requests", async () => {
    const localStorage = new MemoryStorage();
    const sessionStorage = new MemoryStorage();
    vi.stubGlobal("window", {
      localStorage,
      sessionStorage,
      location: { hostname: "localhost", port: "", protocol: "http:" },
    });
    storeToken("expired-access");
    storeRefreshToken("rotating-refresh");

    let refreshCalls = 0;
    const fetchMock = vi.fn(async (input: string | URL | Request) => {
      const url = String(input);
      if (url.endsWith("/auth/refresh")) {
        refreshCalls += 1;
        await Promise.resolve();
        return new Response(
          JSON.stringify({
            access_token: "renewed-access",
            refresh_token: "renewed-refresh",
            token_type: "bearer",
          }),
          { status: 200, headers: { "content-type": "application/json" } },
        );
      }
      const callsForUrl = fetchMock.mock.calls.filter(
        ([candidate]) => String(candidate) === url,
      ).length;
      if (callsForUrl === 1) {
        return new Response(JSON.stringify({ detail: "expired" }), {
          status: 401,
          headers: { "content-type": "application/json" },
        });
      }
      return new Response(JSON.stringify({ url }), {
        status: 200,
        headers: { "content-type": "application/json" },
      });
    });
    vi.stubGlobal("fetch", fetchMock);

    await expect(
      Promise.all([apiFetch("/events/mine"), apiFetch("/event-calendar/mine")]),
    ).resolves.toHaveLength(2);
    expect(refreshCalls).toBe(1);
  });

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

  it("retries a transient gateway response once for safe read requests", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(
        htmlResponse(502, "<!DOCTYPE html><title>Bad gateway</title>"),
      )
      .mockResolvedValueOnce(
        new Response(JSON.stringify([{ id: "task-1" }]), {
          status: 200,
          headers: { "content-type": "application/json" },
        }),
      );
    vi.stubGlobal("fetch", fetchMock);

    await expect(apiFetch("/event-staff-tasks/event-1")).resolves.toEqual([
      { id: "task-1" },
    ]);
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });

  it("never exposes proxy HTML in an application error", async () => {
    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockResolvedValue(
          htmlResponse(502, "<!DOCTYPE html><title>502: Bad gateway</title>"),
        ),
    );

    await expect(
      apiFetch("/event-staff-tasks/event-1", { method: "POST" }),
    ).rejects.toThrow(
      "BTSP is temporarily unavailable. Please try again in a moment.",
    );
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
