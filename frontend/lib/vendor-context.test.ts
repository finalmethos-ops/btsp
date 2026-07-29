import { describe, expect, it } from "vitest";
import { CurrentUser } from "./api";
import { requiresVendorSelection } from "./vendor-context";

const user: CurrentUser = {
  email: "representative@example.com",
  display_name: "Vendor Representative",
  roles: ["VENDOR"],
  permissions: ["vendor.portal"],
  workflows: [],
  vendor_code: null,
  active_vendor_code: null,
  vendor_accounts: [
    { vendor_code: "VENDOR-A", name: "Vendor A" },
    { vendor_code: "VENDOR-B", name: "Vendor B" },
  ],
  login_context: "standard",
  password_change_required: false,
};

describe("requiresVendorSelection", () => {
  it("requires a standard-portal multi-vendor representative to select an account", () => {
    expect(requiresVendorSelection(user)).toBe(true);
  });

  it("allows access after the vendor context is active", () => {
    expect(
      requiresVendorSelection({
        ...user,
        vendor_code: "VENDOR-A",
        active_vendor_code: "VENDOR-A",
      }),
    ).toBe(false);
  });

  it("does not intercept event sessions", () => {
    expect(requiresVendorSelection({ ...user, login_context: "event" })).toBe(
      false,
    );
  });
});
