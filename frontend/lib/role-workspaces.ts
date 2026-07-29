export type RoleWorkspaceModule = {
  title: string;
  description: string;
  href?: string;
  badge?: string;
  attentionQueue?: "vendor" | "purchasing";
};

export type RoleWorkspace = {
  roleLabel: string;
  headline: string;
  summary: string;
  modules: RoleWorkspaceModule[];
};

export const rolePriority = [
  "SYSTEM_ADMIN",
  "ADMIN",
  "PURCHASING",
  "RECONCILIATION",
  "VENDOR",
  "FRANCHISE_OPERATOR",
  "EXECUTIVE",
] as const;

export const roleWorkspaces: Record<string, RoleWorkspace> = {
  FRANCHISE_OPERATOR: {
    roleLabel: "Franchise Operator",
    headline: "Your event essentials, all in one place.",
    summary:
      "A focused view of assigned events, schedules, maps, updates, and conversations.",
    modules: [
      {
        title: "Assigned Events",
        description: "Open the events assigned to your franchise identity.",
        badge: "Event scoped",
      },
      {
        title: "Event Schedule",
        description: "Review dates, sessions, deadlines, and operating hours.",
        badge: "Event scoped",
      },
      {
        title: "Event Maps",
        description:
          "Find venues, floors, vendor areas, and service locations.",
        badge: "Event scoped",
      },
    ],
  },
  VENDOR: {
    roleLabel: "Vendor",
    headline: "Manage your business with Buddy's.",
    summary:
      "Models, requests, approved purchase orders, invoices, and reports—scoped to your vendor identity.",
    modules: [
      {
        title: "Vendor Profile",
        description: "Configure MOQ levels and directional combination rules.",
        href: "/vendor-profile",
      },
      {
        title: "Model Management",
        description:
          "Edit individual models, review cost history, and import or export Excel batches.",
        href: "/vendor-models",
      },
      {
        title: "Order Requests",
        description: "Create and track requests for your available models.",
        href: "/vendor-order-requests",
      },
      {
        title: "Accept PO",
        description:
          "Print or email, then accept with an ETA or reject the locked PO.",
        href: "/vendor-po-acceptance",
      },
      {
        title: "Active POs",
        description: "Update ETA and report backorders or out-of-stock units.",
        href: "/vendor-active-pos",
      },
      {
        title: "POs Needing Attention",
        description: "Accept or deny Purchasing changes and ETA requests.",
        href: "/vendor-po-attention",
        attentionQueue: "vendor",
      },
      {
        title: "Submit Invoices",
        description: "Send invoices against your approved purchase orders.",
        href: "/invoice-intake",
      },
      {
        title: "Reports",
        description:
          "Review monthly and annual spend by Department and Product Code.",
        href: "/vendor-reports",
      },
    ],
  },
  PURCHASING: {
    roleLabel: "Purchasing",
    headline: "Move every request from review to receipt.",
    summary:
      "A streamlined operating view for approvals, purchase orders, catalog, and store management.",
    modules: [
      {
        title: "Order Requests",
        description: "Review and approve vendor and store purchasing requests.",
        href: "/purchasing-order-review",
      },
      {
        title: "PO Review",
        description: "Monitor active and rejected POs, receiving, and handoff.",
        href: "/purchasing-po-monitor",
      },
      {
        title: "POs Needing Attention",
        description:
          "Resolve vendor backorders, stock issues, and substitutes.",
        href: "/purchasing-po-attention",
        attentionQueue: "purchasing",
      },
      {
        title: "Model Catalog",
        description: "Review the complete vendor and product catalog.",
        href: "/model-catalog",
      },
      {
        title: "Store Directory",
        description: "Review and maintain entity, region, and store records.",
        href: "/stores",
      },
    ],
  },
  RECONCILIATION: {
    roleLabel: "Reconciliation",
    headline: "Resolve exceptions and close the loop.",
    summary:
      "Focus on problematic invoices, corrections, vendor communication, and final completion decisions.",
    modules: [
      {
        title: "Submit Invoices",
        description:
          "Upload emailed invoice PDFs into the shared intake queue.",
        href: "/invoice-intake",
      },
      {
        title: "Model Catalog",
        description:
          "Search model details and historical costs for invoice validation.",
        href: "/model-catalog",
      },
      {
        title: "Store Database",
        description:
          "Search store, entity, region, program, address, and time-zone details.",
        href: "/stores",
      },
      {
        title: "Invoice Exceptions",
        description: "Review mismatches and problematic invoice records.",
        href: "/invoices",
      },
      {
        title: "Resolution Workspace",
        description:
          "Correct invoice records and document exception decisions.",
        href: "/invoices",
      },
      {
        title: "Complete Purchase Orders",
        description: "Confirm reconciled POs are ready for completion.",
        href: "/reconciliation-purchase-orders",
      },
    ],
  },
  EXECUTIVE: {
    roleLabel: "Executive",
    headline: "See the signal, skip the noise.",
    summary:
      "Mid- and high-level oversight of purchasing performance, vendors, approvals, receiving, and reconciliation.",
    modules: [
      {
        title: "Executive Analytics",
        description: "Review purchasing, receiving, and reconciliation KPIs.",
        href: "/analytics",
      },
      {
        title: "Reports",
        description: "Open scheduled and historical management reports.",
        href: "/reports",
      },
      {
        title: "Vendor Performance",
        description: "Compare delivery, acknowledgement, and exception trends.",
        href: "/vendor-performance",
      },
    ],
  },
  ADMIN: {
    roleLabel: "Administrator",
    headline: "Operate and govern the whole platform.",
    summary:
      "Oversight across every workspace, identity, vendor, event, workflow, notification, and system control.",
    modules: [
      {
        title: "Administration",
        description:
          "Manage users, roles, workflows, notifications, and health.",
        href: "/admin",
      },
      {
        title: "Purchasing Operations",
        description: "Open purchasing requests, POs, receiving, and invoices.",
        href: "/purchase-orders",
      },
      {
        title: "Analytics",
        description:
          "Review platform-wide reporting and operational performance.",
        href: "/analytics",
      },
      {
        title: "Vendor Management",
        description: "Add vendors and oversee vendor-scoped access.",
        href: "/vendor-connectors",
      },
      {
        title: "Event Management",
        description:
          "Create events, schedules, maps, and operator assignments.",
        badge: "Admin",
        href: "/admin/events",
      },
    ],
  },
};

roleWorkspaces.SYSTEM_ADMIN = roleWorkspaces.ADMIN;
