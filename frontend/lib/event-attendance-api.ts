import { apiFetch } from "./api";

export type EventAttendanceMember = {
  membership_id: string;
  user_id: number;
  display_name: string;
  email: string;
  membership_type:
    | "staff"
    | "vendor"
    | "franchise_representative"
    | "executive"
    | "admin";
  vendor_code: string | null;
  entity_code: string | null;
  pass_code: string;
  status: "registered" | "checked_in" | "checked_out";
  checked_in_at: string | null;
  checked_out_at: string | null;
};

export type EventAttendanceRoster = {
  event_id: string;
  sub_event_id: string;
  sub_event_name: string;
  capacity: number | null;
  registered_total: number;
  checked_in_total: number;
  checked_out_total: number;
  onsite_total: number;
  members: EventAttendanceMember[];
};

export type EventAttendancePassSubEvent = {
  id: string;
  event_id: string;
  name: string;
  location: string;
  starts_at: string;
  ends_at: string;
  module_codes: string[];
  check_in_enabled: boolean;
  status: "registered" | "checked_in" | "checked_out";
  checked_in_at: string | null;
  checked_out_at: string | null;
};

export type EventAttendancePass = {
  event_id: string;
  event_name: string;
  membership_id: string;
  display_name: string;
  email: string;
  membership_type:
    | "staff"
    | "vendor"
    | "franchise_representative"
    | "executive"
    | "admin";
  vendor_code: string | null;
  entity_code: string | null;
  pass_code: string;
  sub_events: EventAttendancePassSubEvent[];
};

export const getMyEventPasses = () =>
  apiFetch<EventAttendancePass[]>("/event-attendance/mine");

export const getEventAttendance = (subEventId: string) =>
  apiFetch<EventAttendanceRoster>(`/event-attendance/${subEventId}`);

export const setEventAttendance = (
  subEventId: string,
  membershipId: string,
  status: "checked_in" | "checked_out",
) =>
  apiFetch<EventAttendanceRoster>(
    `/event-attendance/${subEventId}/members/${membershipId}`,
    { method: "PUT", body: JSON.stringify({ status }) },
  );

export const checkInEventPass = (
  subEventId: string,
  passCode: string,
  status: "checked_in" | "checked_out" = "checked_in",
) =>
  apiFetch<{ roster: EventAttendanceRoster; member: EventAttendanceMember }>(
    `/event-attendance/${subEventId}/pass-check-in`,
    { method: "POST", body: JSON.stringify({ pass_code: passCode, status }) },
  );
