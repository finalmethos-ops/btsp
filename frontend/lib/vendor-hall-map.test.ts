import { describe, expect, it } from "vitest";
import { orderBoothVisitGroups } from "./vendor-hall-map";

const booth = (id: string, x: number, y: number) => ({
  id,
  map_x: String(x),
  map_y: String(y),
});

describe("Vendor Hall visit ordering", () => {
  it("starts near the entrance and proceeds from the latest stop", () => {
    const ordered = orderBoothVisitGroups(
      [
        [booth("far", 10, 10)],
        [booth("entry", 50, 85)],
        [booth("middle", 45, 50)],
      ],
      { x: 50, y: 100 },
    );
    expect(ordered.map((group) => group[0].id)).toEqual([
      "entry",
      "middle",
      "far",
    ]);
  });

  it("keeps colocated shared-booth records as one visit", () => {
    const shared = [booth("sealy", 30, 40), booth("sherwood", 30, 40)];
    expect(orderBoothVisitGroups([shared])[0]).toEqual(shared);
  });
});
