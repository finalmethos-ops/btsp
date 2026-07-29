import { apiDownloadWithFilename, apiFetch } from "./api";

export type EventStaffTaskStatus =
  | "open"
  | "in_progress"
  | "done"
  | "blocked"
  | "cancelled";
export type EventStaffTaskPriority = "low" | "normal" | "high" | "urgent";
export type EventStaffTaskPhase = "pre_event" | "live_event" | "post_event";

export type EventStaffTaskAttachment = {
  id: string;
  task_id: string;
  filename: string;
  content_type: string;
  uploaded_by: string;
  created_at: string;
};

export type EventStaffTask = {
  id: string;
  event_id: string;
  event_name: string;
  sub_event_id: string | null;
  sub_event_name: string | null;
  vendor_hall_booth_name: string | null;
  vendor_hall_booth_id: string | null;
  assigned_membership_id: string;
  assigned_display_name: string;
  assigned_email: string;
  title: string;
  description: string | null;
  priority: EventStaffTaskPriority;
  status: EventStaffTaskStatus;
  status_note: string | null;
  task_phase: EventStaffTaskPhase;
  due_at: string | null;
  completed_at: string | null;
  completed_by: string | null;
  attachments: EventStaffTaskAttachment[];
  updated_at: string;
};

export type EventStaffTaskWrite = Omit<
  EventStaffTask,
  | "id"
  | "event_id"
  | "event_name"
  | "sub_event_name"
  | "vendor_hall_booth_name"
  | "assigned_display_name"
  | "assigned_email"
  | "status_note"
  | "completed_at"
  | "completed_by"
  | "attachments"
  | "updated_at"
>;

export const listEventStaffTasks = (eventId: string) =>
  apiFetch<EventStaffTask[]>(`/event-staff-tasks/${eventId}`);

export const listMyEventStaffTasks = () =>
  apiFetch<EventStaffTask[]>("/event-staff-tasks/mine");

export const createEventStaffTask = (
  eventId: string,
  payload: EventStaffTaskWrite,
) =>
  apiFetch<EventStaffTask>(`/event-staff-tasks/${eventId}`, {
    method: "POST",
    body: JSON.stringify(payload),
  });

export const updateEventStaffTask = (
  eventId: string,
  taskId: string,
  payload: EventStaffTaskWrite,
) =>
  apiFetch<EventStaffTask>(`/event-staff-tasks/${eventId}/${taskId}`, {
    method: "PUT",
    body: JSON.stringify(payload),
  });

export const updateMyEventStaffTaskStatus = (
  taskId: string,
  status: EventStaffTaskStatus,
  note?: string,
) =>
  apiFetch<EventStaffTask>(`/event-staff-tasks/${taskId}/status`, {
    method: "PATCH",
    body: JSON.stringify({ status, note: note?.trim() || null }),
  });

export const uploadEventStaffTaskEvidence = (taskId: string, file: File) => {
  const body = new FormData();
  body.append("file", file);
  return apiFetch<EventStaffTaskAttachment>(
    `/event-staff-tasks/${encodeURIComponent(taskId)}/attachments`,
    { method: "POST", body },
  );
};

export const downloadEventStaffTaskEvidence = (
  taskId: string,
  attachmentId: string,
) =>
  apiDownloadWithFilename(
    `/event-staff-tasks/${encodeURIComponent(taskId)}/attachments/${encodeURIComponent(attachmentId)}/content`,
  );

export const exportEventStaffTasks = (eventId: string) =>
  apiDownloadWithFilename(
    `/event-staff-tasks/events/${encodeURIComponent(eventId)}/export.xlsx`,
  );
