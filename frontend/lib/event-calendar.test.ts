import { describe, expect, it } from "vitest";
import { EventCalendarEntry } from "./event-calendar-api";
import {
  calendarEntryTiming,
  eventCalendarFilename,
  eventCalendarIcs,
} from "./event-calendar";

const entry: EventCalendarEntry = {
  id: "entry-1",
  event_id: "event-1",
  event_name: "Leadership & Vendor Fair",
  entry_type: "sub_event",
  sub_event_id: "sub-event-1",
  module_codes: ["ordering"],
  title: "Live Buying, Session 1",
  description: "Products; pricing\nand ordering",
  starts_at: "2026-08-11T13:00:00Z",
  ends_at: "2026-08-11T14:00:00Z",
  location: "Hall A, Booth 12",
  visibility_categories: ["vendor"],
  is_active: true,
  updated_at: "2026-07-12T12:00:00Z",
};

describe("event calendar utilities", () => {
  it("classifies past, live, and upcoming calendar entries", () => {
    expect(calendarEntryTiming(entry, new Date("2026-08-11T12:00:00Z"))).toBe(
      "upcoming",
    );
    expect(calendarEntryTiming(entry, new Date("2026-08-11T13:30:00Z"))).toBe(
      "live",
    );
    expect(calendarEntryTiming(entry, new Date("2026-08-11T14:00:00Z"))).toBe(
      "past",
    );
  });

  it("exports visible entries as an escaped standard calendar", () => {
    const calendar = eventCalendarIcs(
      [entry],
      new Date("2026-07-12T12:00:00Z"),
    );
    expect(calendar).toContain("BEGIN:VCALENDAR\r\nVERSION:2.0");
    expect(calendar).toContain("DTSTART:20260811T130000Z");
    expect(calendar).toContain("SUMMARY:Live Buying\\, Session 1");
    expect(calendar).toContain(
      "DESCRIPTION:Products\\; pricing\\nand ordering",
    );
    expect(calendar).toContain("LOCATION:Hall A\\, Booth 12");
  });

  it("creates a safe schedule filename", () => {
    expect(eventCalendarFilename(entry.event_name)).toBe(
      "leadership-vendor-fair-schedule.ics",
    );
  });
});
