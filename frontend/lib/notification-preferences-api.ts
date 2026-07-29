import { apiFetch } from "./api";

export type NotificationPreferences = {
  user_id: number;
  in_app_enabled: boolean;
  email_enabled: boolean;
  quiet_hours_start: string | null;
  quiet_hours_end: string | null;
};

export const getNotificationPreferences = () =>
  apiFetch<NotificationPreferences>("/notifications/preferences");

export const saveNotificationPreferences = (
  payload: Omit<NotificationPreferences, "user_id">,
) =>
  apiFetch<NotificationPreferences>("/notifications/preferences", {
    method: "PUT",
    body: JSON.stringify(payload),
  });
