import { apiDownload, apiFetch } from "./api";

export type PurchaseOrderSource = {
  purchase_request_id: string;
  store_number: string;
};
export type PurchaseOrderLine = {
  id: number;
  source_request_id: string;
  source_line_id: number;
  store_number: string;
  product_code: string;
  product_name: string;
  quantity: string;
  unit_price: string;
  freight_amount: string;
  tax_amount: string;
  extended_amount: string;
  notes: string | null;
};
export type PurchaseOrder = {
  id: string;
  po_number: string;
  workflow_code: string;
  vendor_code: string;
  status: string;
  currency: string;
  subtotal: string;
  freight_total: string;
  tax_total: string;
  total: string;
  created_by: string;
  created_at: string;
  updated_at: string;
  sources: PurchaseOrderSource[];
  lines: PurchaseOrderLine[];
};
export type PurchaseOrderArtifact = {
  id: string;
  purchase_order_id: string;
  artifact_format: "pdf" | "csv" | "json";
  version: number;
  content_type: string;
  size_bytes: number;
  sha256: string;
  created_by: string;
  created_at: string;
};
export type TransmissionEvent = {
  id: number;
  event_type: string;
  from_status: string | null;
  to_status: string;
  reason: string | null;
  actor: string;
  created_at: string;
};
export type PurchaseOrderTransmission = {
  id: string;
  purchase_order_id: string;
  artifact_id: string;
  channel: "manual" | "secure_file" | "internal_email";
  destination: string | null;
  status: string;
  notes: string | null;
  created_by: string;
  updated_by: string;
  created_at: string;
  updated_at: string;
  events: TransmissionEvent[];
};

export const listPurchaseOrders = () =>
  apiFetch<PurchaseOrder[]>("/purchase-orders");
export const getPurchaseOrder = (id: string) =>
  apiFetch<PurchaseOrder>(`/purchase-orders/${id}`);
export const generatePurchaseOrders = (requestIds: string[]) =>
  apiFetch<PurchaseOrder[]>("/purchase-orders/generate", {
    method: "POST",
    body: JSON.stringify({ purchase_request_ids: requestIds }),
  });
export const listPurchaseOrderArtifacts = (id: string) =>
  apiFetch<PurchaseOrderArtifact[]>(`/purchase-orders/${id}/artifacts`);
export const generatePurchaseOrderArtifact = (
  id: string,
  format: "pdf" | "csv" | "json",
) =>
  apiFetch<PurchaseOrderArtifact>(
    `/purchase-orders/${id}/artifacts/${format}`,
    { method: "POST" },
  );
export const downloadPurchaseOrderArtifact = (id: string, artifactId: string) =>
  apiDownload(`/purchase-orders/${id}/artifacts/${artifactId}/content`);
export const listPurchaseOrderTransmissions = (id: string) =>
  apiFetch<PurchaseOrderTransmission[]>(`/purchase-orders/${id}/transmissions`);
export const createPurchaseOrderTransmission = (
  id: string,
  payload: {
    artifact_id: string;
    channel: string;
    destination?: string;
    notes?: string;
  },
) =>
  apiFetch<PurchaseOrderTransmission>(`/purchase-orders/${id}/transmissions`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
export const runPurchaseOrderTransmissionAction = (
  orderId: string,
  transmissionId: string,
  action: string,
  reason?: string,
) =>
  apiFetch<PurchaseOrderTransmission>(
    `/purchase-orders/${orderId}/transmissions/${transmissionId}/actions`,
    {
      method: "POST",
      body: JSON.stringify({ action, reason: reason || null }),
    },
  );
