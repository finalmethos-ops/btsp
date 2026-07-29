import { describe, expect, it } from "vitest";
import { loadoutWorkspaceMode, resolveEventLoadoutRole } from "./loadout-role";

describe("loadout role routing", () => {
  it("prioritizes a role assigned to the selected sub-event", () => {
    expect(
      resolveEventLoadoutRole({
        subEventRole: "overseer",
        eventRole: "dockmaster",
        membershipType: "admin",
      }),
    ).toBe("overseer");
  });

  it("falls back to the event role when the sub-event role is blank", () => {
    expect(
      resolveEventLoadoutRole({
        subEventRole: null,
        eventRole: "dockmaster",
        membershipType: "admin",
      }),
    ).toBe("dockmaster");
  });

  it("supports legacy loadout membership types", () => {
    expect(
      resolveEventLoadoutRole({
        subEventRole: null,
        eventRole: null,
        membershipType: "team_lead",
      }),
    ).toBe("team_lead");
  });

  it("keeps all three operational workspaces isolated", () => {
    expect(
      loadoutWorkspaceMode({
        role: "team_lead",
        isAdmin: true,
        isExecutive: false,
      }),
    ).toBe("team_lead");
    expect(
      loadoutWorkspaceMode({
        role: "dockmaster",
        isAdmin: true,
        isExecutive: false,
      }),
    ).toBe("dockmaster");
    expect(
      loadoutWorkspaceMode({
        role: "overseer",
        isAdmin: true,
        isExecutive: false,
      }),
    ).toBe("overseer");
  });

  it("routes unscoped users without granting executive operations", () => {
    expect(
      loadoutWorkspaceMode({
        role: null,
        isAdmin: true,
        isExecutive: false,
      }),
    ).toBe("admin");
    expect(
      loadoutWorkspaceMode({
        role: null,
        isAdmin: false,
        isExecutive: false,
      }),
    ).toBe("participant");
    expect(
      loadoutWorkspaceMode({
        role: null,
        isAdmin: false,
        isExecutive: true,
      }),
    ).toBeNull();
  });
});
