import { apiFetch } from "@/lib/api";

export type ReceiptLine = {
  id: number;
  purchase_order_line_id: number;
  product_code: string;
  received_quantity: string;
  accepted_quantity: string;
  rejected_quantity: string;
  rejection_reason: string | null;
};

export type PurchaseReceipt = {
  id: string;
  receipt_number: string;
  purchase_order_id: string;
  store_number: string;
  external_receipt_id: string | null;
  status: string;
  packing_slip_number: string | null;
  received_at: string;
  received_by: string;
  lines: ReceiptLine[];
  variances: ReceiptVariance[];
};

export type ReceiptVariance = {
  id: string;
  receipt_id: string;
  receipt_line_id: number;
  variance_type: string;
  severity: string;
  expected_quantity: string;
  actual_quantity: string;
  difference_quantity: string;
  status: string;
  resolution_note: string | null;
};

export type PurchaseBackorder = {
  id: string;
  backorder_number: string;
  source_variance_id: string;
  store_number: string;
  product_code: string;
  original_quantity: string;
  fulfilled_quantity: string;
  outstanding_quantity: string;
  status: string;
  substitute_product_code: string | null;
};

export const listReceipts = () => apiFetch<PurchaseReceipt[]>("/receipts");

export const createReceipt = (payload: Record<string, unknown>) =>
  apiFetch<PurchaseReceipt>("/receipts", {
    method: "POST",
    body: JSON.stringify(payload),
  });

export const listOpenVariances = () =>
  apiFetch<ReceiptVariance[]>("/receipts/variances/open");

export const resolveVariance = (
  varianceId: string,
  action: "resolve" | "waive",
  note: string,
) =>
  apiFetch<ReceiptVariance>(
    `/receipts/variances/${encodeURIComponent(varianceId)}/resolution`,
    {
      method: "POST",
      body: JSON.stringify({ action, note }),
    },
  );

export const listBackorders = () =>
  apiFetch<PurchaseBackorder[]>("/receipts/backorders/list");

export const createBackorder = (varianceId: string, note: string) =>
  apiFetch<PurchaseBackorder>("/receipts/backorders/create", {
    method: "POST",
    body: JSON.stringify({ source_variance_id: varianceId, note }),
  });

export const runBackorderAction = (
  backorderId: string,
  payload: Record<string, unknown>,
) =>
  apiFetch<PurchaseBackorder>(
    `/receipts/backorders/${encodeURIComponent(backorderId)}/actions`,
    { method: "POST", body: JSON.stringify(payload) },
  );
