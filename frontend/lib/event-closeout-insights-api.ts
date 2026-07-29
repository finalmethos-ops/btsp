import { apiFetch } from "./api";

export type EventCloseoutInsights = {
  event_id: string;
  event_name: string;
  status: string;
  vendor_hall_status: string | null;
  vendor_hall_closeout_ready: boolean | null;
  readiness_percentage: number | string;
  order_total: number;
  order_released: number;
  approved_units: number;
  approved_spend: string;
  loadout_assignment_total: number;
  loadout_released: number;
  open_exception_count: number;
  feedback_response_count: number;
  feedback_eligible_attendee_count: number;
  feedback_response_rate: number | string;
  feedback_average_rating: number | string | null;
  order_to_loadout_rate: number | string;
  approved_at: string | null;
  closed_at: string | null;
};

export const getEventCloseoutInsights = (eventId: string) =>
  apiFetch<EventCloseoutInsights>(`/event-closeout-insights/${eventId}`);
