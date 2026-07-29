import { describe, expect, it } from "vitest";
import { archivedEventYears, filterArchivedEvents } from "./event-archive";

const events = [
  {
    name: "Leadership Meeting",
    venue_name: "Orlando Convention Center",
    city: "Orlando",
    state_code: "FL",
    slug: "leadership-meeting",
    status: "completed" as const,
    ends_at: "2027-07-13T20:00:00Z",
  },
  {
    name: "Cancelled Vendor Fair",
    venue_name: "Expo Hall",
    city: "Tampa",
    state_code: "FL",
    slug: "cancelled-vendor-fair",
    status: "cancelled" as const,
    ends_at: "2026-04-05T20:00:00Z",
  },
];

describe("archived event filtering", () => {
  it("searches event and location fields without case sensitivity", () => {
    expect(
      filterArchivedEvents(events, {
        search: "ORLANDO",
        status: "all",
        year: "all",
      }),
    ).toEqual([events[0]]);
  });

  it("combines lifecycle status and end-year filters", () => {
    expect(
      filterArchivedEvents(events, {
        search: "",
        status: "cancelled",
        year: "2026",
      }),
    ).toEqual([events[1]]);
  });

  it("returns archive years newest first", () => {
    expect(archivedEventYears(events)).toEqual([2027, 2026]);
  });
});
