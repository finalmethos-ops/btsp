import type { CurrentUser } from "./api";

/**
 * Return the one action a user should receive for a live presentation.
 * The presentation itself is intentionally reserved for presenter/projector
 * sessions; attendees are sent to their role-specific workspace instead.
 */
export function liveEventDestination(
  user: CurrentUser | null,
  eventId: string,
  subEventId: string,
): string {
  const roles = new Set(user?.roles ?? []);
  if (roles.has("FRANCHISE_OPERATOR")) {
    return `/events/order/${subEventId}`;
  }
  if (roles.has("VENDOR")) {
    return `/events/live-overview/${subEventId}`;
  }
  if (roles.has("EXECUTIVE")) {
    return `/events/live-overview/${subEventId}`;
  }
  if (roles.has("ADMIN") || roles.has("SYSTEM_ADMIN")) {
    return `/events?event_id=${encodeURIComponent(eventId)}`;
  }
  return `/events/calendar?event_id=${encodeURIComponent(eventId)}`;
}
