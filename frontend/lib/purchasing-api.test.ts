import { afterEach, describe, expect, it, vi } from "vitest";
import { createPurchaseRequest, listProducts } from "./purchasing-api";

function response(payload: unknown) {
  return { ok: true, status: 200, json: async () => payload } as Response;
}

afterEach(() => vi.unstubAllGlobals());

describe("purchasing API", () => {
  it("encodes catalog search and vendor filters", async () => {
    const fetchMock = vi.fn().mockResolvedValue(response([]));
    vi.stubGlobal("fetch", fetchMock);
    await listProducts("V-100", "display rack");
    expect(fetchMock.mock.calls[0][0]).toContain(
      "/catalog/products?vendor_code=V-100&search=display+rack",
    );
  });

  it("creates requests using the selected workflow boundary", async () => {
    const payload = {
      workflow_code: "IND_PURCHASING",
      store_number: "1001",
      vendor_code: "V-100",
    };
    const fetchMock = vi.fn().mockResolvedValue(response({ id: "request-1" }));
    vi.stubGlobal("fetch", fetchMock);
    await createPurchaseRequest(payload);
    expect(fetchMock.mock.calls[0][1]).toMatchObject({
      method: "POST",
      body: JSON.stringify(payload),
    });
  });
});
