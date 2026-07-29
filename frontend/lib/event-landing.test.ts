import { describe, expect, it } from "vitest";
import { eventLandingPath, usesCalendarEventLanding } from "./event-landing";

const user = {
  email: "attendee@example.com",
  display_name: "Attendee",
  permissions: [],
  workflows: [],
  vendor_code: null,
  active_vendor_code: null,
  vendor_accounts: [],
  login_context: "event" as const,
  password_change_required: false,
};

describe("event landing routing", () => {
  it.each(["VENDOR", "FRANCHISE_OPERATOR"])(
    "uses the calendar for %s",
    (role) => {
      const attendee = { ...user, roles: [role] };
      expect(usesCalendarEventLanding(attendee)).toBe(true);
      expect(eventLandingPath(attendee)).toBe("/events/calendar");
    },
  );

  it.each(["ADMIN", "SYSTEM_ADMIN", "EXECUTIVE", "EVENT_STAFF"])(
    "starts %s on the event calendar",
    (role) => {
      const operator = { ...user, roles: [role] };
      expect(usesCalendarEventLanding(operator)).toBe(false);
      expect(eventLandingPath(operator)).toBe("/events/calendar");
    },
  );

  it("keeps the selected event in the landing URL", () => {
    const attendee = { ...user, roles: ["VENDOR"] };
    expect(eventLandingPath(attendee, "event / 1")).toBe(
      "/events/calendar?event_id=event%20%2F%201",
    );
  });
});
