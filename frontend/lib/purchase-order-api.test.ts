import { afterEach, describe, expect, it, vi } from "vitest";
import {
  generatePurchaseOrders,
  runPurchaseOrderTransmissionAction,
} from "./purchase-order-api";

function response(payload: unknown) {
  return { ok: true, status: 200, json: async () => payload } as Response;
}

afterEach(() => vi.unstubAllGlobals());

describe("Purchase Order API", () => {
  it("generates from explicit source request identities", async () => {
    const fetchMock = vi.fn().mockResolvedValue(response([]));
    vi.stubGlobal("fetch", fetchMock);

    await generatePurchaseOrders(["request-1", "request-2"]);

    expect(fetchMock.mock.calls[0][1]).toMatchObject({
      method: "POST",
      body: JSON.stringify({
        purchase_request_ids: ["request-1", "request-2"],
      }),
    });
  });

  it("records transmission actions and reasons", async () => {
    const fetchMock = vi.fn().mockResolvedValue(response({ status: "failed" }));
    vi.stubGlobal("fetch", fetchMock);

    await runPurchaseOrderTransmissionAction(
      "order-1",
      "transmission-1",
      "mark_failed",
      "Printer unavailable",
    );

    expect(fetchMock.mock.calls[0][0]).toContain(
      "/purchase-orders/order-1/transmissions/transmission-1/actions",
    );
    expect(fetchMock.mock.calls[0][1]).toMatchObject({
      body: JSON.stringify({
        action: "mark_failed",
        reason: "Printer unavailable",
      }),
    });
  });
});
