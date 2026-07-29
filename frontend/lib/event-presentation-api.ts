import { apiDownload, apiFetch } from "./api";
import { EventProductSlide } from "./event-product-slide-api";

export type EventPresentation = {
  sub_event_id: string;
  event_id: string;
  event_name: string;
  sub_event_name: string;
  status: "idle" | "live" | "ended";
  ordering_status: "open" | "closed";
  ordering_opened_at: string | null;
  current_slide: EventProductSlide | null;
  total_slides: number;
  current_position: number | null;
  total_units_ordered: number;
  total_combined_spend: string;
  sub_event_units_ordered: number;
  sub_event_combined_spend: string;
  presenter_notes: string | null;
  slide_queue: Array<{
    id: string;
    position: number;
    slide_type: "product" | "filler";
    filler_category:
      | "trivia"
      | "giveaway"
      | "sponsorship"
      | "special_thanks"
      | "raffle"
      | null;
    model_number: string | null;
    name: string;
    presenter_notes: string | null;
  }>;
  updated_at: string | null;
};

export type PresentationAction =
  | "start"
  | "previous"
  | "next"
  | "open"
  | "close"
  | "end";

export type EventLiveAnalytics = {
  sub_event_id: string;
  current_slide_id: string | null;
  assigned_entities: number;
  responding_entities: number;
  confirmed_entities: number;
  waitlisted_entities: number;
  entities_remaining: number;
  confirmed_units: number;
  confirmed_spend: string;
  waitlisted_units: number;
  orders: Array<{
    entity_code: string;
    quantity: number;
    total_cost: string;
    status: string;
    updated_at: string;
  }>;
};

export const getEventPresentation = (subEventId: string) =>
  apiFetch<EventPresentation>(`/event-presentations/${subEventId}`);

export const getEventPresenterPresentation = (subEventId: string) =>
  apiFetch<EventPresentation>(`/event-presentations/${subEventId}/presenter`);

export const controlEventPresentation = (
  subEventId: string,
  action: PresentationAction,
) =>
  apiFetch<EventPresentation>(`/event-presentations/${subEventId}/control`, {
    method: "POST",
    body: JSON.stringify({ action }),
  });

export const downloadPresentationImage = (slideId: string) =>
  apiDownload(`/event-product-slides/${slideId}/image`);

export const getEventLiveAnalytics = (subEventId: string) =>
  apiFetch<EventLiveAnalytics>(`/event-presentations/${subEventId}/analytics`);
