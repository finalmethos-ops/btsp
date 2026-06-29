import { describe, expect, it } from "vitest";
import type {
  AdminRoleCreate,
  AdminUserCreate,
  AdminUserUpdate,
  WorkflowDefinitionAdmin,
} from "./api";

describe("user admin payloads", () => {
  it("supports create payload role assignment", () => {
    const payload: AdminUserCreate = {
      email: "manager@example.com",
      display_name: "Manager",
      password: "change-this-password",
      is_active: true,
      role_codes: ["BPP_ADMIN"],
    };

    expect(payload.role_codes).toEqual(["BPP_ADMIN"]);
    expect(payload.is_active).toBe(true);
  });

  it("supports update payload role assignment", () => {
    const payload: AdminUserUpdate = {
      role_codes: ["INDEPENDENT_ADMIN"],
      is_active: false,
    };

    expect(payload.role_codes).toEqual(["INDEPENDENT_ADMIN"]);
    expect(payload.is_active).toBe(false);
  });

  it("supports custom role permission assignment", () => {
    const payload: AdminRoleCreate = {
      code: "REPORT_READER",
      name: "Report Reader",
      permission_codes: ["analytics.read"],
    };

    expect(payload.permission_codes).toEqual(["analytics.read"]);
  });

  it("represents pinned workflow-version instance counts", () => {
    const definition: WorkflowDefinitionAdmin = {
      id: 1,
      code: "BPP_PURCHASING",
      name: "BPP Purchasing",
      version: 2,
      business_area: "Purchasing",
      category: "BPP",
      configuration_namespace: "workflow.bpp",
      states: ["draft", "approved"],
      initial_state: "draft",
      terminal_states: ["approved"],
      transitions: [],
      is_active: true,
      active_instance_count: 3,
      total_instance_count: 8,
      created_at: "2026-06-29T00:00:00Z",
      updated_at: "2026-06-29T00:00:00Z",
    };

    expect(definition.active_instance_count).toBe(3);
    expect(definition.version).toBe(2);
  });
});
