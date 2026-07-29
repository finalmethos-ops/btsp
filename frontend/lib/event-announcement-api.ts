import { apiFetch } from "./api";
import { EventMembership } from "./event-admin-api";

export type AnnouncementAudience = EventMembership["membership_type"];

export type EventAnnouncement = {
  id: string;
  event_id: string;
  event_name: string;
  sub_event_id: string | null;
  sub_event_name: string | null;
  title: string;
  body: string;
  severity: "info" | "important" | "urgent";
  visibility_categories: AnnouncementAudience[];
  publishes_at: string;
  expires_at: string | null;
  is_active: boolean;
  updated_at: string;
};

export type EventAnnouncementWrite = Omit<
  EventAnnouncement,
  "id" | "event_id" | "event_name" | "sub_event_name" | "updated_at"
>;

export const listEventAnnouncements = (eventId: string) =>
  apiFetch<EventAnnouncement[]>(`/event-announcements/${eventId}`);

export const listMyEventAnnouncements = () =>
  apiFetch<EventAnnouncement[]>("/event-announcements/mine");

export const createEventAnnouncement = (
  eventId: string,
  payload: EventAnnouncementWrite,
) =>
  apiFetch<EventAnnouncement>(`/event-announcements/${eventId}`, {
    method: "POST",
    body: JSON.stringify(payload),
  });

export const updateEventAnnouncement = (
  eventId: string,
  announcementId: string,
  payload: EventAnnouncementWrite,
) =>
  apiFetch<EventAnnouncement>(
    `/event-announcements/${eventId}/${announcementId}`,
    {
      method: "PUT",
      body: JSON.stringify(payload),
    },
  );

export const deleteEventAnnouncement = (
  eventId: string,
  announcementId: string,
) =>
  apiFetch<void>(`/event-announcements/${eventId}/${announcementId}`, {
    method: "DELETE",
  });
