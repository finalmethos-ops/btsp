export type EventLoadoutRole = "team_lead" | "dockmaster" | "overseer";

const LOADOUT_ROLES = new Set<EventLoadoutRole>([
  "team_lead",
  "dockmaster",
  "overseer",
]);

export function resolveEventLoadoutRole({
  subEventRole,
  eventRole,
  membershipType,
}: {
  subEventRole?: EventLoadoutRole | null;
  eventRole?: EventLoadoutRole | null;
  membershipType?: string | null;
}): EventLoadoutRole | null {
  if (subEventRole) return subEventRole;
  if (eventRole) return eventRole;
  return LOADOUT_ROLES.has(membershipType as EventLoadoutRole)
    ? (membershipType as EventLoadoutRole)
    : null;
}

export function loadoutWorkspaceMode({
  role,
  isAdmin,
  isExecutive,
}: {
  role: EventLoadoutRole | null;
  isAdmin: boolean;
  isExecutive: boolean;
}): "team_lead" | "dockmaster" | "overseer" | "admin" | "participant" | null {
  if (role) return role;
  if (isAdmin) return "admin";
  if (isExecutive) return null;
  return "participant";
}
