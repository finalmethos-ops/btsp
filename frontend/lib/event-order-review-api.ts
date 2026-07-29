import {
  apiDownloadWithFilename,
  apiFetch,
  sanitizeDownloadFilename,
} from "./api";

export type EventOrderReviewItem = {
  order_id: string;
  sub_event_name: string;
  entity_code: string;
  vendor_code: string;
  model_number: string;
  product_name: string;
  quantity: number;
  unit_cost: string;
  total_cost: string;
  requested_delivery_start: string;
  requested_delivery_end: string;
  live_status: string;
  review_status: string;
  reviewed_by: string | null;
  reviewed_at: string | null;
  variant_lines: Array<{
    model_number: string;
    product_name: string;
    quantity: number;
    unit_cost: string;
    total_cost: string;
  }>;
  purchasing_requests: Array<{
    purchase_request_id: string;
    order_number: string;
    status: string;
  }>;
};

export type EventOrderReviewSummary = {
  event_id: string;
  event_name: string;
  pending: number;
  approved: number;
  rejected: number;
  released: number;
  approved_units: number;
  approved_spend: string;
  items: EventOrderReviewItem[];
};

export type EventOrderRelease = {
  batch_id: string;
  event_id: string;
  order_count: number;
  vendor_count: number;
  entity_count: number;
  total_units: number;
  total_spend: string;
  purchase_request_count: number;
  status: string;
  created_at: string;
};

export type EventOrderBackupArtifact = {
  id: string;
  event_id: string;
  filename: string;
  content_type: string;
  size_bytes: number;
  sha256: string;
  created_by: string;
  created_at: string;
};

export const getEventOrderReview = (eventId: string) =>
  apiFetch<EventOrderReviewSummary>(`/event-order-review/${eventId}`);

export const decideEventOrder = (
  orderId: string,
  payload: {
    decision: "approve" | "reject" | "revise";
    revised_quantity?: number | null;
    reason?: string | null;
  },
) =>
  apiFetch<EventOrderReviewSummary>(`/event-order-review/orders/${orderId}`, {
    method: "PUT",
    body: JSON.stringify(payload),
  });

export const releaseEventOrders = (eventId: string) =>
  apiFetch<EventOrderRelease>(`/event-order-review/${eventId}/release`, {
    method: "POST",
  });

export const getArchivedEventOrderBackup = (eventId: string) =>
  apiFetch<EventOrderBackupArtifact>(
    `/event-order-review/${eventId}/archived-backup`,
  );

export async function exportEventOrders(eventId: string) {
  const download = await apiDownloadWithFilename(
    `/event-order-review/${eventId}/export.csv`,
  );
  const url = URL.createObjectURL(download.blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = download.filename ?? `event-${eventId}-orders.csv`;
  anchor.click();
  URL.revokeObjectURL(url);
}

export async function exportEventOrderBackup(
  eventId: string,
  eventName: string,
) {
  const download = await apiDownloadWithFilename(
    `/event-order-review/${eventId}/backup.xlsx`,
  );
  const url = URL.createObjectURL(download.blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download =
    download.filename ??
    `${sanitizeDownloadFilename(eventName)?.replaceAll(" ", "-") ?? eventId}-all-orders.xlsx`;
  anchor.click();
  URL.revokeObjectURL(url);
}

export async function downloadArchivedEventOrderBackup(
  eventId: string,
  eventName: string,
) {
  const download = await apiDownloadWithFilename(
    `/event-order-review/${eventId}/archived-backup.xlsx`,
  );
  const url = URL.createObjectURL(download.blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download =
    download.filename ??
    `${sanitizeDownloadFilename(eventName)?.replaceAll(" ", "-") ?? eventId}-all-orders.xlsx`;
  anchor.click();
  URL.revokeObjectURL(url);
}
