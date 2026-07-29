import { describe, expect, it } from "vitest";
import { hasPermission, visibleAdminNavigation } from "./permissions";

const testUser = {
  email: "admin@example.com",
  display_name: "Admin",
  roles: ["SYSTEM_ADMIN"],
  permissions: ["system.admin", "configuration.manage"],
  workflows: [],
  vendor_code: null,
  active_vendor_code: null,
  vendor_accounts: [],
  login_context: "standard" as const,
  password_change_required: false,
};

describe("access helpers", () => {
  it("checks permission membership", () => {
    expect(hasPermission(testUser, "system.admin")).toBe(true);
    expect(hasPermission(testUser, "snapshots.read")).toBe(false);
  });

  it("filters admin links by permission", () => {
    const labels = visibleAdminNavigation(testUser).map((item) => item.label);

    expect(labels).toContain("Users");
    expect(labels).toContain("Configuration");
    expect(labels).not.toContain("Audit");
  });
});
