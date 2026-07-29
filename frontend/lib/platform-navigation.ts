import type { CurrentUser } from "./api";

type PlatformNavigationItem = {
  label: string;
  href: string;
  group?: PlatformNavigationGroup;
  permissions?: string[];
};

export const platformNavigationGroups = [
  "Purchasing",
  "Insights & Directories",
  "Events",
  "Administration",
] as const;

export type PlatformNavigationGroup = (typeof platformNavigationGroups)[number];

const platformNavigationItems: PlatformNavigationItem[] = [
  { label: "Command Center", href: "/" },
  {
    label: "Purchasing Operations",
    href: "/purchase-orders",
    group: "Purchasing",
    permissions: [
      "system.admin",
      "orders.bpp.manage",
      "orders.independent.manage",
    ],
  },
  {
    label: "Order Review",
    href: "/purchasing-order-review",
    group: "Purchasing",
    permissions: ["purchase_orders.handoff"],
  },
  {
    label: "PO Monitor",
    href: "/purchasing-po-monitor",
    group: "Purchasing",
    permissions: ["purchase_orders.handoff"],
  },
  {
    label: "Receiving",
    href: "/receiving",
    group: "Purchasing",
    permissions: ["receiving.read"],
  },
  {
    label: "Inventory Ledger",
    href: "/inventory",
    group: "Purchasing",
    permissions: ["receiving.read"],
  },
  {
    label: "Invoices",
    href: "/invoices",
    group: "Purchasing",
    permissions: ["invoices.read"],
  },
  {
    label: "Analytics",
    href: "/analytics",
    group: "Insights & Directories",
    permissions: ["analytics.read"],
  },
  {
    label: "Vendor Management",
    href: "/vendor-connectors",
    group: "Insights & Directories",
    permissions: ["vendor.integrations.read"],
  },
  {
    label: "Model Catalog",
    href: "/model-catalog",
    group: "Insights & Directories",
    permissions: ["catalog.models.read"],
  },
  {
    label: "Store Directory",
    href: "/stores",
    group: "Insights & Directories",
    permissions: ["stores.read"],
  },
  {
    label: "Event Management",
    href: "/admin/events",
    group: "Events",
    permissions: ["events.manage"],
  },
  {
    label: "My Events",
    href: "/events",
    group: "Events",
    permissions: ["events.read", "events.manage"],
  },
  {
    label: "Archived Events",
    href: "/events/archive",
    group: "Events",
    permissions: ["events.manage"],
  },
  {
    label: "Vendor Management",
    href: "/admin/vendor-management",
    group: "Administration",
    permissions: ["system.admin"],
  },
  {
    label: "Buddy’s Users",
    href: "/admin/buddys-users",
    group: "Administration",
    permissions: ["system.admin"],
  },
  {
    label: "Roles",
    href: "/admin/roles",
    group: "Administration",
    permissions: ["roles.manage"],
  },
  {
    label: "Workflows",
    href: "/admin/workflows",
    group: "Administration",
    permissions: ["workflows.manage"],
  },
  {
    label: "Notifications",
    href: "/admin/notifications",
    group: "Administration",
    permissions: ["notifications.manage"],
  },
  {
    label: "System Health",
    href: "/admin/system-health",
    group: "Administration",
    permissions: ["system.health.read"],
  },
  {
    label: "Configuration",
    href: "/admin/configuration",
    group: "Administration",
    permissions: ["configuration.manage"],
  },
  {
    label: "Audit",
    href: "/admin/audit",
    group: "Administration",
    permissions: ["snapshots.read"],
  },
];

export function visiblePlatformNavigation(user: CurrentUser | null) {
  if (!user) return [];
  return platformNavigationItems.filter(
    (item) =>
      !item.permissions ||
      item.permissions.some((permission) =>
        user.permissions.includes(permission),
      ),
  );
}
