import { apiDownload, apiFetch } from "./api";
import { PurchaseOrder } from "./purchase-order-api";
import { PurchaseRequest } from "./purchasing-api";
import { VendorModel } from "./vendor-model-api";
import type { PurchaseOrderFilterValues } from "@/components/PurchaseOrderFilters";

const poFilterQuery = (filters?: Partial<PurchaseOrderFilterValues>) => {
  const params = new URLSearchParams();
  Object.entries(filters ?? {}).forEach(([key, value]) => {
    if (value) params.set(key, value);
  });
  return params.toString();
};

export type LifecycleLinePayload = {
  product_code: string;
  quantity: number;
  notes?: string | null;
};

export const listVendorOrderRequests = () =>
  apiFetch<PurchaseRequest[]>("/order-lifecycle/vendor/requests");
export const createVendorOrderRequests = (
  store_numbers: string[],
  expected_delivery_date: string,
  line_items: LifecycleLinePayload[],
) =>
  apiFetch<PurchaseRequest[]>("/order-lifecycle/vendor/requests/bulk", {
    method: "POST",
    body: JSON.stringify({
      store_numbers,
      expected_delivery_date,
      line_items,
    }),
  });
export const deleteVendorOrderRequest = (id: string) =>
  apiFetch<void>(`/order-lifecycle/vendor/requests/${id}`, {
    method: "DELETE",
  });
export const updateVendorOrderRequestDate = (
  id: string,
  expected_delivery_date: string,
) =>
  apiFetch<PurchaseRequest>(
    `/order-lifecycle/vendor/requests/${id}/expected-delivery`,
    {
      method: "PATCH",
      body: JSON.stringify({ expected_delivery_date }),
    },
  );
export const addVendorRequestLine = (
  id: string,
  payload: LifecycleLinePayload,
) =>
  apiFetch<PurchaseRequest>(`/order-lifecycle/vendor/requests/${id}/lines`, {
    method: "PUT",
    body: JSON.stringify(payload),
  });
export const updateVendorRequestLine = (
  id: string,
  lineId: number,
  payload: LifecycleLinePayload,
) =>
  apiFetch<PurchaseRequest>(
    `/order-lifecycle/vendor/requests/${id}/lines/${lineId}`,
    { method: "PUT", body: JSON.stringify(payload) },
  );
export const deleteVendorRequestLine = (id: string, lineId: number) =>
  apiFetch<PurchaseRequest>(
    `/order-lifecycle/vendor/requests/${id}/lines/${lineId}`,
    { method: "DELETE" },
  );
export const submitVendorOrderRequest = (id: string) =>
  apiFetch<PurchaseRequest>(`/order-lifecycle/vendor/requests/${id}/submit`, {
    method: "POST",
  });

export const listPurchasingOrderRequests = () =>
  apiFetch<PurchaseRequest[]>("/order-lifecycle/purchasing/requests");
export const addPurchasingRequestLine = (
  id: string,
  payload: LifecycleLinePayload,
) =>
  apiFetch<PurchaseRequest>(
    `/order-lifecycle/purchasing/requests/${id}/lines`,
    {
      method: "PUT",
      body: JSON.stringify(payload),
    },
  );
export const updatePurchasingRequestLine = (
  id: string,
  lineId: number,
  payload: LifecycleLinePayload,
) =>
  apiFetch<PurchaseRequest>(
    `/order-lifecycle/purchasing/requests/${id}/lines/${lineId}`,
    { method: "PUT", body: JSON.stringify(payload) },
  );
export const deletePurchasingRequestLine = (id: string, lineId: number) =>
  apiFetch<PurchaseRequest>(
    `/order-lifecycle/purchasing/requests/${id}/lines/${lineId}`,
    { method: "DELETE" },
  );
export const decidePurchasingRequest = (
  id: string,
  action: "approve" | "cancel",
  reason?: string,
  expectedDeliveryDate?: string,
) =>
  apiFetch<{ status: string; purchase_order_id: string | null }>(
    `/order-lifecycle/purchasing/requests/${id}/decision`,
    {
      method: "POST",
      body: JSON.stringify({
        action,
        reason: reason || null,
        expected_delivery_date: expectedDeliveryDate || null,
      }),
    },
  );

export const listVendorPOs = (
  queue: "pending" | "active" | "attention" | "rejected",
  filters?: Partial<PurchaseOrderFilterValues>,
) =>
  apiFetch<PurchaseOrder[]>(
    `/order-lifecycle/vendor/pos?queue=${queue}&${poFilterQuery(filters)}`,
  );
export const respondToVendorPO = (
  id: string,
  action: "accept" | "reject",
  eta?: string,
  reason?: string,
) =>
  apiFetch<PurchaseOrder>(`/order-lifecycle/vendor/pos/${id}/respond`, {
    method: "POST",
    body: JSON.stringify({ action, eta: eta || null, reason: reason || null }),
  });
export const downloadVendorPO = (id: string) =>
  apiDownload(`/order-lifecycle/vendor/pos/${id}/print`);
export const getVendorPOEmailDetails = (id: string) =>
  apiFetch<{ recipient: string | null; subject: string; body: string }>(
    `/order-lifecycle/vendor/pos/${id}/email-details`,
  );

export const listPurchasingLifecyclePOs = (
  queue: "active" | "attention" | "rejected" | "inactive",
  filters?: Partial<PurchaseOrderFilterValues>,
) =>
  apiFetch<PurchaseOrder[]>(
    `/order-lifecycle/purchasing/pos?queue=${queue}&${poFilterQuery(filters)}`,
  );
export const receiveLifecyclePOLine = (
  orderId: string,
  lineId: number,
  quantity: number,
) =>
  apiFetch<PurchaseOrder>(
    `/order-lifecycle/purchasing/pos/${orderId}/lines/${lineId}/receive`,
    { method: "POST", body: JSON.stringify({ quantity }) },
  );
export const handoffLifecyclePO = (orderId: string) =>
  apiFetch<PurchaseOrder>(
    `/order-lifecycle/purchasing/pos/${orderId}/handoff`,
    {
      method: "POST",
    },
  );
export const completeLifecyclePO = (orderId: string) =>
  apiFetch<PurchaseOrder>(
    `/order-lifecycle/reconciliation/pos/${orderId}/complete`,
    {
      method: "POST",
    },
  );

export const updateVendorPOEta = (orderId: string, eta: string) =>
  apiFetch<PurchaseOrder>(`/order-lifecycle/vendor/pos/${orderId}/eta`, {
    method: "PATCH",
    body: JSON.stringify({ eta }),
  });

export const reportVendorPOIssue = (
  orderId: string,
  payload: {
    action: "backorder" | "out_of_stock";
    line_id: number;
    quantity: number;
    eta?: string | null;
    substitute_product_code?: string | null;
    reason?: string | null;
  },
) =>
  apiFetch<PurchaseOrder>(`/order-lifecycle/vendor/pos/${orderId}/issues`, {
    method: "POST",
    body: JSON.stringify(payload),
  });

export const listVendorSubstituteOptions = (orderId: string, lineId: number) =>
  apiFetch<VendorModel[]>(
    `/order-lifecycle/vendor/pos/${orderId}/lines/${lineId}/substitute-options`,
  );

export const requestPurchasingPOChange = (
  orderId: string,
  payload: {
    action:
      | "cancel"
      | "add_model"
      | "remove_units"
      | "delay"
      | "expedite"
      | "request_eta";
    line_id?: number | null;
    product_code?: string | null;
    quantity?: number | null;
    requested_date?: string | null;
    reason: string;
  },
) =>
  apiFetch<PurchaseOrder>(
    `/order-lifecycle/purchasing/pos/${orderId}/changes`,
    { method: "POST", body: JSON.stringify(payload) },
  );

export const respondVendorPOAttention = (
  orderId: string,
  attentionId: string,
  action: "accept" | "deny" | "confirm",
  eta?: string,
  note?: string,
) =>
  apiFetch<PurchaseOrder>(
    `/order-lifecycle/vendor/pos/${orderId}/attention/${attentionId}/respond`,
    {
      method: "POST",
      body: JSON.stringify({ action, eta: eta || null, note: note || null }),
    },
  );

export const acknowledgePurchasingPOAttention = (
  orderId: string,
  attentionId: string,
  note?: string,
) =>
  apiFetch<PurchaseOrder>(
    `/order-lifecycle/purchasing/pos/${orderId}/attention/${attentionId}/acknowledge`,
    {
      method: "POST",
      body: JSON.stringify({ action: "acknowledge", note: note || null }),
    },
  );

export const removeAttentionModel = (orderId: string, attentionId: string) =>
  apiFetch<PurchaseOrder>(
    `/order-lifecycle/purchasing/pos/${orderId}/attention/${attentionId}/remove-model`,
    { method: "POST" },
  );
