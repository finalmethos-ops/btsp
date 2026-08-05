import { afterEach, describe, expect, it, vi } from "vitest";
import { getPublicEventPresentation } from "./event-presentation-api";

afterEach(() => vi.unstubAllGlobals());

describe("projector presentation access", () => {
  it("uses only the scoped projector token and does not require a user session", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      json: async () => ({ sub_event_id: "sub-event-1" }),
      ok: true,
      status: 200,
    } as Response);
    vi.stubGlobal("fetch", fetchMock);

    await getPublicEventPresentation("sub-event-1", "projector-token");

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/v1/public-event-presentations/sub-event-1",
      {
        headers: { "X-BTSP-Projector-Token": "projector-token" },
      },
    );
    expect(fetchMock.mock.calls[0][1].headers).not.toHaveProperty(
      "Authorization",
    );
  });
});
