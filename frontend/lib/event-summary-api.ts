import { apiFetch } from "./api";

export type EventSummary = {
  event_id: string;
  event_name: string;
  scope: "operations" | "vendor" | "buddys";
  vendor_code: string | null;
  entity_code: string | null;
  region_code: string | null;
  total_order_count: number;
  total_units: number;
  total_spend: string;
  sub_events: Array<{
    sub_event_id: string;
    sub_event_name: string;
    order_count: number;
    units: number;
    spend: string;
  }>;
  vendors: Array<{
    code: string;
    order_count: number;
    units: number;
    spend: string;
    average_order_spend: string;
  }>;
  entities: Array<{
    code: string;
    order_count: number;
    units: number;
    spend: string;
    average_order_spend: string;
  }>;
  departments: Array<{
    code: string;
    order_count: number;
    units: number;
    spend: string;
    average_order_spend: string;
  }>;
};

export const getEventSummary = (eventId: string) =>
  apiFetch<EventSummary>(`/event-summary/${encodeURIComponent(eventId)}`);
