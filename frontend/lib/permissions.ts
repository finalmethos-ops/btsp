import type { CurrentUser } from "./api";

export function hasPermission(
  user: CurrentUser | null,
  permissionCode: string,
): boolean {
  return Boolean(user?.permissions.includes(permissionCode));
}

export function hasAnyPermission(
  user: CurrentUser | null,
  permissionCodes: string[],
): boolean {
  return permissionCodes.some((permissionCode) =>
    hasPermission(user, permissionCode),
  );
}

export type AdminNavigationItem = {
  label: string;
  href: string;
  permission: string;
};

export const adminNavigationItems: AdminNavigationItem[] = [
  { label: "Users", href: "/admin/users", permission: "system.admin" },
  { label: "Roles", href: "/admin/roles", permission: "roles.manage" },
  {
    label: "Workflows",
    href: "/admin/workflows",
    permission: "workflows.manage",
  },
  {
    label: "Notifications",
    href: "/admin/notifications",
    permission: "notifications.manage",
  },
  {
    label: "System Health",
    href: "/admin/system-health",
    permission: "system.health.read",
  },
  {
    label: "Configuration",
    href: "/admin/configuration",
    permission: "configuration.manage",
  },
  { label: "Audit", href: "/admin/audit", permission: "snapshots.read" },
];

export function visibleAdminNavigation(
  user: CurrentUser | null,
): AdminNavigationItem[] {
  return adminNavigationItems.filter((item) =>
    hasPermission(user, item.permission),
  );
}
