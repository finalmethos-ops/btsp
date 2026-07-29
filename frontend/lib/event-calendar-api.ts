import { apiFetch } from "./api";
import { EventMembership } from "./event-admin-api";

export type CalendarAudience = EventMembership["membership_type"];

export type EventCalendarEntry = {
  id: string;
  event_id: string;
  event_name: string;
  entry_type: "text" | "sub_event";
  sub_event_id: string | null;
  module_codes: string[];
  title: string;
  description: string | null;
  starts_at: string;
  ends_at: string;
  location: string | null;
  visibility_categories: CalendarAudience[];
  is_active: boolean;
  sub_event_accessible?: boolean;
  updated_at: string;
};

export type EventCalendarWrite = Omit<
  EventCalendarEntry,
  | "id"
  | "event_id"
  | "event_name"
  | "module_codes"
  | "sub_event_accessible"
  | "updated_at"
>;

export const listEventCalendar = (eventId: string) =>
  apiFetch<EventCalendarEntry[]>(`/event-calendar/${eventId}`);

export const listMyEventCalendar = () =>
  apiFetch<EventCalendarEntry[]>("/event-calendar/mine");

export const createEventCalendarEntry = (
  eventId: string,
  payload: EventCalendarWrite,
) =>
  apiFetch<EventCalendarEntry>(`/event-calendar/${eventId}`, {
    method: "POST",
    body: JSON.stringify(payload),
  });

export const updateEventCalendarEntry = (
  eventId: string,
  entryId: string,
  payload: EventCalendarWrite,
) =>
  apiFetch<EventCalendarEntry>(`/event-calendar/${eventId}/${entryId}`, {
    method: "PUT",
    body: JSON.stringify(payload),
  });

export const deleteEventCalendarEntry = (eventId: string, entryId: string) =>
  apiFetch<void>(`/event-calendar/${eventId}/${entryId}`, {
    method: "DELETE",
  });
