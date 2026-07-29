import { apiDownloadWithFilename, apiFetch } from "./api";
import { LifecycleLinePayload } from "./order-lifecycle-api";
import { EligibleStore, PurchaseRequest } from "./purchasing-api";

export type EventBuyFairModel = {
  product_code: string;
  model_identifier: string;
  name: string;
  unit_price: string;
  currency: string;
  minimum_order_quantity: string;
  is_booth_model: boolean;
};

export type EventBuyFairWorkspace = {
  event_id: string;
  event_name: string;
  sub_event_id: string;
  sub_event_name: string;
  vendor_code: string;
  models: EventBuyFairModel[];
  stores: EligibleStore[];
  requesters: Array<{
    id: number;
    display_name: string;
    entity_code: string | null;
    region_code: string | null;
  }>;
  orders: PurchaseRequest[];
  order_count: number;
  total_units: string;
  total_volume: string;
};

export type EventBuyFairSummary = {
  event_id: string;
  sub_event_id: string | null;
  vendor_count: number;
  order_count: number;
  draft_count: number;
  submitted_count: number;
  total_units: string;
  total_volume: string;
  vendors: Array<{
    vendor_code: string;
    order_count: number;
    draft_count: number;
    submitted_count: number;
    total_units: string;
    total_volume: string;
  }>;
  orders: Array<{
    id: string;
    order_number: string;
    vendor_code: string;
    store_number: string;
    requester_name: string | null;
    requester_email: string | null;
    requester_entity_code: string | null;
    requester_region_code: string | null;
    status: string;
    expected_delivery_date: string | null;
    total_units: string;
    total_volume: string;
    created_at: string;
  }>;
};

const base = (subEventId: string) =>
  `/event-buy-fair/${encodeURIComponent(subEventId)}`;

export const getEventBuyFairWorkspace = (subEventId: string) =>
  apiFetch<EventBuyFairWorkspace>(base(subEventId));

export const getEventBuyFairSummary = (eventId: string) =>
  apiFetch<EventBuyFairSummary>(
    `/event-buy-fair/events/${encodeURIComponent(eventId)}/summary`,
  );

export const getSubEventBuyFairSummary = (subEventId: string) =>
  apiFetch<EventBuyFairSummary>(
    `/event-buy-fair/sub-events/${encodeURIComponent(subEventId)}/summary`,
  );

export async function downloadEventBuyFairOrders(eventId: string) {
  const download = await apiDownloadWithFilename(
    `/event-buy-fair/events/${encodeURIComponent(eventId)}/export`,
  );
  const url = URL.createObjectURL(download.blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = download.filename ?? "vendor-buy-fair-orders.csv";
  anchor.click();
  URL.revokeObjectURL(url);
}

export async function downloadSubEventBuyFairOrders(subEventId: string) {
  const download = await apiDownloadWithFilename(
    `/event-buy-fair/sub-events/${encodeURIComponent(subEventId)}/export`,
  );
  const url = URL.createObjectURL(download.blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = download.filename ?? "vendor-buy-fair-sub-event-orders.csv";
  anchor.click();
  URL.revokeObjectURL(url);
}

export const createEventBuyFairOrders = (
  subEventId: string,
  requester_id: number,
  store_numbers: string[],
  expected_delivery_date: string,
  line_items: LifecycleLinePayload[],
) =>
  apiFetch<PurchaseRequest[]>(`${base(subEventId)}/orders`, {
    method: "POST",
    body: JSON.stringify({
      requester_id,
      store_numbers,
      expected_delivery_date,
      line_items,
    }),
  });

export const updateEventBuyFairOrderDate = (
  subEventId: string,
  requestId: string,
  expected_delivery_date: string,
) =>
  apiFetch<PurchaseRequest>(
    `${base(subEventId)}/orders/${requestId}/expected-delivery`,
    { method: "PATCH", body: JSON.stringify({ expected_delivery_date }) },
  );

export const addEventBuyFairLine = (
  subEventId: string,
  requestId: string,
  payload: LifecycleLinePayload,
) =>
  apiFetch<PurchaseRequest>(`${base(subEventId)}/orders/${requestId}/lines`, {
    method: "PUT",
    body: JSON.stringify(payload),
  });

export const removeEventBuyFairLine = (
  subEventId: string,
  requestId: string,
  lineId: number,
) =>
  apiFetch<PurchaseRequest>(
    `${base(subEventId)}/orders/${requestId}/lines/${lineId}`,
    { method: "DELETE" },
  );

export const submitEventBuyFairOrder = (
  subEventId: string,
  requestId: string,
) =>
  apiFetch<PurchaseRequest>(`${base(subEventId)}/orders/${requestId}/submit`, {
    method: "POST",
  });

export const deleteEventBuyFairOrder = (
  subEventId: string,
  requestId: string,
) =>
  apiFetch<void>(`${base(subEventId)}/orders/${requestId}`, {
    method: "DELETE",
  });
