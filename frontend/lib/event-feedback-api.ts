import { apiFetch } from "./api";

export type EventFeedbackSummary = {
  event_id: string;
  response_count: number;
  eligible_attendee_count: number;
  response_rate: number;
  feedback_by_attendee_type: Array<{
    attendee_type: string;
    response_count: number;
    average_rating: number | null;
  }>;
  average_rating: number | null;
  submitted_by_current_user: boolean;
  responses: Array<{
    id: string;
    rating: number;
    comments: string | null;
    created_at: string;
  }>;
};

export const getEventFeedback = (eventId: string) =>
  apiFetch<EventFeedbackSummary>(`/event-feedback/${eventId}`);

export const submitEventFeedback = (
  eventId: string,
  rating: number,
  comments: string,
) =>
  apiFetch<EventFeedbackSummary>(`/event-feedback/${eventId}`, {
    method: "PUT",
    body: JSON.stringify({ rating, comments: comments || null }),
  });
