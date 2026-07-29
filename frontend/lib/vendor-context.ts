import { CurrentUser } from "./api";

export function requiresVendorSelection(user: CurrentUser | null): boolean {
  return Boolean(
    user?.login_context === "standard" &&
      user.roles.includes("VENDOR") &&
      user.vendor_accounts.length > 1 &&
      !user.active_vendor_code,
  );
}
