import { apiDownload, apiFetch } from "./api";

export type EventMembership = {
  id: string;
  event_id: string;
  user_id: number;
  email: string;
  display_name: string;
  membership_type:
    | "staff"
    | "vendor"
    | "franchise_representative"
    | "executive"
    | "admin"
    | "team_lead"
    | "dockmaster"
    | "overseer";
  loadout_role: "team_lead" | "dockmaster" | "overseer" | null;
  sub_event_roles: Record<
    string,
    "team_lead" | "dockmaster" | "overseer" | null
  >;
  vendor_code: string | null;
  vendor_codes: string[];
  entity_code: string | null;
  module_codes: string[];
  task_scope: string | null;
  is_active: boolean;
  sub_event_scope_configured: boolean;
  sub_event_ids: string[];
};

export type ManagedSubEvent = {
  id: string;
  event_id: string;
  name: string;
  description: string | null;
  starts_at: string;
  ends_at: string;
  location: string;
  status: "draft" | "published" | "completed" | "cancelled";
  module_codes: string[];
  capacity: number | null;
};

export type ManagedEvent = {
  id: string;
  slug: string;
  name: string;
  description: string | null;
  status: "draft" | "published" | "completed" | "cancelled";
  starts_at: string;
  ends_at: string;
  timezone: string;
  venue_name: string;
  address_line1: string;
  address_line2: string | null;
  city: string;
  state_code: string;
  postal_code: string;
  country_code: string;
  theme_primary_color: string;
  theme_accent_color: string;
  cancelled_at: string | null;
  cancelled_by: string | null;
  cancellation_reason: string | null;
  created_by: string;
  created_at: string;
  has_branding: boolean;
  has_venue_map: boolean;
  sub_events: ManagedSubEvent[];
  memberships: EventMembership[];
};

export type EventModule = { code: string; name: string };
export type EventAccountDirectoryEntry = {
  id: number;
  email: string;
  display_name: string;
  is_active: boolean;
  vendor_codes: string[];
};

export type EventWrite = Omit<
  ManagedEvent,
  | "id"
  | "created_by"
  | "created_at"
  | "has_branding"
  | "has_venue_map"
  | "sub_events"
  | "memberships"
  | "cancelled_at"
  | "cancelled_by"
  | "cancellation_reason"
>;

export const listManagedEvents = () => apiFetch<ManagedEvent[]>("/events");
export const listMyEvents = () => apiFetch<ManagedEvent[]>("/events/mine");
export const listArchivedEvents = () =>
  apiFetch<ManagedEvent[]>("/events/archive");
export const listEventModules = () =>
  apiFetch<EventModule[]>("/events/modules");
export const listEventAccountDirectory = () =>
  apiFetch<EventAccountDirectoryEntry[]>("/events/account-directory");

export const createManagedEvent = (payload: EventWrite) =>
  apiFetch<ManagedEvent>("/events", {
    method: "POST",
    body: JSON.stringify(payload),
  });

export const updateManagedEvent = (eventId: string, payload: EventWrite) =>
  apiFetch<ManagedEvent>(`/events/${eventId}`, {
    method: "PUT",
    body: JSON.stringify(payload),
  });

export const cancelManagedEvent = (eventId: string, reason: string) =>
  apiFetch<ManagedEvent>(`/events/${eventId}/cancel`, {
    method: "POST",
    body: JSON.stringify({ reason }),
  });

export const publishManagedEvent = (eventId: string) =>
  apiFetch<ManagedEvent>(`/events/${eventId}/publish`, { method: "POST" });

export const deleteManagedEvent = (eventId: string) =>
  apiFetch<void>(`/events/${eventId}`, { method: "DELETE" });

export const addManagedSubEvent = (
  eventId: string,
  payload: Omit<ManagedSubEvent, "id" | "event_id">,
) =>
  apiFetch<ManagedEvent>(`/events/${eventId}/sub-events`, {
    method: "POST",
    body: JSON.stringify(payload),
  });

export const updateManagedSubEvent = (
  eventId: string,
  subEventId: string,
  payload: Omit<ManagedSubEvent, "id" | "event_id">,
) =>
  apiFetch<ManagedEvent>(`/events/${eventId}/sub-events/${subEventId}`, {
    method: "PUT",
    body: JSON.stringify(payload),
  });

export const deleteManagedSubEvent = (eventId: string, subEventId: string) =>
  apiFetch<ManagedEvent>(`/events/${eventId}/sub-events/${subEventId}`, {
    method: "DELETE",
  });

export const updateSubEventModules = (
  eventId: string,
  subEventId: string,
  moduleCodes: string[],
) =>
  apiFetch<ManagedEvent>(
    `/events/${eventId}/sub-events/${subEventId}/modules`,
    {
      method: "PUT",
      body: JSON.stringify({ module_codes: moduleCodes }),
    },
  );

export const addEventMembership = (
  eventId: string,
  payload: {
    email: string;
    display_name: string;
    password?: string | null;
    membership_type:
      | "staff"
      | "vendor"
      | "franchise_representative"
      | "executive"
      | "admin"
      | "team_lead"
      | "dockmaster"
      | "overseer";
    vendor_code?: string | null;
    vendor_codes?: string[];
    entity_code?: string | null;
    module_codes: string[];
    task_scope?: string | null;
    is_active: boolean;
  },
) =>
  apiFetch<ManagedEvent>(`/events/${eventId}/memberships`, {
    method: "POST",
    body: JSON.stringify(payload),
  });

export const assignEventMembershipSubEvents = (
  eventId: string,
  membershipId: string,
  subEventIds: string[],
  roles: EventMembership["sub_event_roles"] = {},
) =>
  apiFetch<ManagedEvent>(
    `/events/${eventId}/memberships/${membershipId}/sub-events`,
    {
      method: "PUT",
      body: JSON.stringify({ sub_event_ids: subEventIds, roles }),
    },
  );

export const updateEventMembershipRole = (
  eventId: string,
  membershipId: string,
  membershipType: EventMembership["membership_type"],
) =>
  apiFetch<ManagedEvent>(
    `/events/${eventId}/memberships/${membershipId}/role`,
    {
      method: "PUT",
      body: JSON.stringify({ membership_type: membershipType }),
    },
  );

export const updateEventMembershipLoadoutRole = (
  eventId: string,
  membershipId: string,
  loadoutRole: EventMembership["loadout_role"],
) =>
  apiFetch<ManagedEvent>(
    `/events/${eventId}/memberships/${membershipId}/loadout-role`,
    { method: "PUT", body: JSON.stringify({ loadout_role: loadoutRole }) },
  );

export const updateEventMembershipVendors = (
  eventId: string,
  membershipId: string,
  vendorCodes: string[],
) =>
  apiFetch<ManagedEvent>(
    `/events/${eventId}/memberships/${membershipId}/vendors`,
    {
      method: "PUT",
      body: JSON.stringify({ vendor_codes: vendorCodes }),
    },
  );

export const uploadEventBranding = (eventId: string, file: File) => {
  const body = new FormData();
  body.append("file", file);
  return apiFetch<ManagedEvent>(`/events/${eventId}/branding`, {
    method: "POST",
    body,
  });
};

export const downloadEventBranding = (eventId: string) =>
  apiDownload(`/events/${eventId}/branding`);

export const uploadEventVenueMap = (eventId: string, file: File) => {
  const body = new FormData();
  body.append("file", file);
  return apiFetch<ManagedEvent>(`/events/${eventId}/venue-map`, {
    method: "POST",
    body,
  });
};

export const downloadEventVenueMap = (eventId: string) =>
  apiDownload(`/events/${eventId}/venue-map`);
