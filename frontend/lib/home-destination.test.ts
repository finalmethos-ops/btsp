import { describe, expect, it } from "vitest";
import type { CurrentUser } from "./api";
import { homeDestination } from "./home-destination";

const user = (overrides: Partial<CurrentUser> = {}): CurrentUser => ({
  email: "user@example.com",
  display_name: "Test User",
  roles: ["PURCHASING_ADMIN"],
  permissions: [],
  workflows: [],
  vendor_code: null,
  active_vendor_code: null,
  vendor_accounts: [],
  login_context: "standard",
  password_change_required: false,
  ...overrides,
});

describe("homeDestination", () => {
  it("returns the command center for standard portal modules", () => {
    expect(homeDestination(user())).toMatchObject({
      href: "/",
      label: "Command center",
    });
  });

  it("returns the event calendar for every event-login module", () => {
    expect(
      homeDestination(
        user({ login_context: "event", permissions: ["events.manage"] }),
      ),
    ).toMatchObject({ href: "/events/calendar", label: "Event home" });
  });

  it("keeps standard-login vendor and attendee accounts in the standard portal", () => {
    expect(
      homeDestination(
        user({
          roles: ["VENDOR"],
          permissions: ["events.read"],
        }),
      ),
    ).toMatchObject({ href: "/", label: "Command center" });
  });
});
