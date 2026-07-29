import type { CurrentUser } from "./api";

const EVENT_OPERATIONS_ROLES = new Set([
  "ADMIN",
  "SYSTEM_ADMIN",
  "EXECUTIVE",
  "EVENT_STAFF",
]);

export function usesCalendarEventLanding(user: CurrentUser | null): boolean {
  return Boolean(
    user && !user.roles.some((role) => EVENT_OPERATIONS_ROLES.has(role)),
  );
}

export function eventLandingPath(
  _user: CurrentUser | null,
  eventId?: string,
): string {
  // Every event login starts at the branded calendar. Operations users can
  // still open the full administrative command center from there, but it is
  // never the default while they are attending the show.
  const path = "/events/calendar";
  return eventId ? `${path}?event_id=${encodeURIComponent(eventId)}` : path;
}
