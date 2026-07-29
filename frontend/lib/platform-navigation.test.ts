import { describe, expect, it } from "vitest";
import { visiblePlatformNavigation } from "./platform-navigation";

const admin = {
  email: "admin@example.com",
  display_name: "Admin",
  roles: ["ADMIN"],
  permissions: [
    "system.admin",
    "purchase_orders.handoff",
    "receiving.read",
    "invoices.read",
    "analytics.read",
    "vendor.integrations.read",
    "catalog.models.read",
    "stores.read",
    "events.read",
    "events.manage",
    "roles.manage",
    "workflows.manage",
    "notifications.manage",
    "system.health.read",
    "configuration.manage",
    "snapshots.read",
  ],
  workflows: [],
  vendor_code: null,
  active_vendor_code: null,
  vendor_accounts: [],
  login_context: "standard" as const,
  password_change_required: false,
};

describe("platform navigation", () => {
  it("keeps operational and administrative controls in one admin navigation", () => {
    const labels = visiblePlatformNavigation(admin).map((item) => item.label);

    expect(labels).toContain("Command Center");
    expect(labels).toContain("Purchasing Operations");
    expect(labels).toContain("Event Management");
    expect(labels).toContain("Archived Events");
    expect(labels).toContain("Vendor Management");
    expect(labels).toContain("Buddy’s Users");
    expect(labels).toContain("Audit");
    expect(labels).not.toContain("Administration Home");
  });

  it("does not expose controls without permission", () => {
    const labels = visiblePlatformNavigation({
      ...admin,
      permissions: ["events.read"],
    }).map((item) => item.label);

    expect(labels).toEqual(["Command Center", "My Events"]);
  });
});
