import { apiFetch } from "./api";

export type VendorLiveProductMetric = {
  slide_id: string;
  position: number;
  vendor_code: string;
  vendor_name: string;
  model_number: string;
  name: string;
  units_ordered: number;
  committed_spend: string;
};

export type VendorLiveVendorMetric = {
  vendor_code: string;
  vendor_name: string;
  units_ordered: number;
  committed_spend: string;
};

export type EventLiveInsights = {
  event_id: string;
  event_name: string;
  sub_event_id: string;
  sub_event_name: string;
  scope: "executive" | "vendor" | "franchise";
  presentation_status: string;
  ordering_status: string;
  current_position: number | null;
  total_slides: number;
  sub_event_units: number;
  sub_event_spend: string;
  responding_entities: number;
  entity_code: string | null;
  franchise_sub_event_units: number;
  franchise_sub_event_spend: string;
  vendor_code: string | null;
  vendor_name: string | null;
  vendor_sub_event_units: number;
  vendor_sub_event_spend: string;
  slides_until_next_product: number | null;
  next_vendor_code: string | null;
  next_vendor_name: string | null;
  vendor_totals: VendorLiveVendorMetric[];
  vendor_products: VendorLiveProductMetric[];
};

export const getEventLiveInsights = (subEventId: string) =>
  apiFetch<EventLiveInsights>(`/event-live-insights/${subEventId}`);
