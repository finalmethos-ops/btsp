import { apiFetch } from "./api";

export type NotificationEvent = {
  notification_id: number;
  template_code: string;
  workflow_code: string;
  event_type: string;
  entity_type: string;
  entity_id: string;
  actor: string;
  channel: string;
  resolved_recipients: string[];
  subject: string;
  body: string;
  action_href: string | null;
  status: string;
  created_at: string;
  sent_at: string | null;
};

export const listNotificationHistory = () =>
  apiFetch<NotificationEvent[]>("/notifications/mine?limit=200");

export const retryNotification = (notificationId: number) =>
  apiFetch<NotificationEvent>(`/notifications/events/${notificationId}/retry`, {
    method: "POST",
  });
