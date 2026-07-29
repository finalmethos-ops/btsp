import { apiFetch } from "./api";
import { EventProductSlide } from "./event-product-slide-api";

export type EventOrder = {
  id: string;
  slide_id: string;
  entity_code: string;
  quantity: number;
  requested_delivery_start: string;
  requested_delivery_end: string;
  unit_cost: string;
  total_cost: string;
  status: "confirmed" | "waitlisted";
  variant_quantities: Record<string, number>;
  submitted_at: string;
  updated_at: string;
};

export type EventOrderingWorkspace = {
  event_id: string;
  event_name: string;
  sub_event_id: string;
  sub_event_name: string;
  entity_code: string;
  ordering_status: "open" | "closed";
  ordering_opened_at: string | null;
  presentation_status: "idle" | "live" | "ended";
  current_slide: EventProductSlide | null;
  existing_order: EventOrder | null;
  units_remaining: number | null;
  entity_sub_event_spend: string;
};

export const getEventOrderingWorkspace = (subEventId: string) =>
  apiFetch<EventOrderingWorkspace>(`/event-ordering/${subEventId}`);

export const submitEventOrder = (
  subEventId: string,
  payload: {
    quantity: number;
    variant_quantities?: Record<string, number>;
  },
) =>
  apiFetch<EventOrderingWorkspace>(`/event-ordering/${subEventId}/order`, {
    method: "PUT",
    body: JSON.stringify(payload),
  });
