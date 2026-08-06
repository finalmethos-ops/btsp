import { apiDownload, apiFetch } from "./api";

export type CatalogVendor = {
  vendor_code: string;
  name: string;
  is_active: boolean;
};
export type EligibleStore = {
  store_number: string;
  name: string;
  entity_code: string | null;
  region_code: string;
  city: string | null;
  state_code: string | null;
};
export type CatalogProduct = {
  product_code: string;
  model_identifier: string;
  vendor_code: string;
  name: string;
  model_number: string | null;
  department: string | null;
  product_category_code: string | null;
  brand: string | null;
  unit_price: string;
  currency: string;
  minimum_order_quantity: string;
  is_available: boolean;
  is_active: boolean;
};
export type PurchaseLine = {
  id: number;
  product_code: string;
  model_identifier: string;
  product_name: string;
  quantity: string;
  unit_price: string;
  freight_amount: string;
  tax_amount: string;
  extended_amount: string;
  notes: string | null;
};
export type PurchaseRequest = {
  id: string;
  order_number: string;
  workflow_code: string;
  workflow_instance_id: number | null;
  store_number: string;
  vendor_code: string;
  status: string;
  currency: string;
  subtotal: string;
  freight_total: string;
  tax_total: string;
  total: string;
  expected_delivery_date: string | null;
  context: Record<string, unknown>;
  revision: number;
  expires_at: string | null;
  cloned_from_id: string | null;
  created_by: string;
  updated_by: string;
  created_at: string;
  updated_at: string;
  line_items: PurchaseLine[];
};
export type ValidationIssue = {
  code: string;
  field: string | null;
  message: string;
};
export type PurchaseValidation = {
  ready: boolean;
  errors: ValidationIssue[];
  warnings: ValidationIssue[];
};
export type Attachment = {
  id: string;
  purchase_request_id: string;
  category: string;
  original_filename: string;
  content_type: string;
  size_bytes: number;
  sha256: string;
  uploaded_by: string;
  created_at: string;
};
export type WorkflowInstance = {
  id: number;
  current_state: string;
  status: string;
  updated_at: string;
};

export const listVendors = (activeOnly = true) =>
  apiFetch<CatalogVendor[]>(`/catalog/vendors?active_only=${activeOnly}`);
export const createCatalogVendor = (vendor_code: string, name: string) =>
  apiFetch<CatalogVendor>("/catalog/vendors", {
    method: "POST",
    body: JSON.stringify({ vendor_code, name }),
  });
export const updateCatalogVendor = (
  vendorCode: string,
  payload: { name?: string; is_active?: boolean },
) =>
  apiFetch<CatalogVendor>(`/catalog/vendors/${vendorCode}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
export const listEligibleStores = (vendorCode: string) =>
  apiFetch<EligibleStore[]>(
    `/stores/eligible?vendor_code=${encodeURIComponent(vendorCode)}`,
  );
export const listProducts = (vendorCode: string, search = "") => {
  const params = new URLSearchParams({ vendor_code: vendorCode });
  if (search) params.set("search", search);
  return apiFetch<CatalogProduct[]>(`/catalog/products?${params}`);
};
export const listPurchaseRequests = (status?: string) =>
  apiFetch<PurchaseRequest[]>(
    `/purchase-requests${status ? `?request_status=${encodeURIComponent(status)}` : ""}`,
  );
export const createPurchaseRequest = (payload: {
  workflow_code: string;
  store_number: string;
  vendor_code: string;
}) =>
  apiFetch<PurchaseRequest>("/purchase-requests", {
    method: "POST",
    body: JSON.stringify(payload),
  });
export const getPurchaseRequest = (id: string) =>
  apiFetch<PurchaseRequest>(`/purchase-requests/${id}`);
export const addPurchaseLine = (id: string, payload: Record<string, unknown>) =>
  apiFetch<PurchaseLine>(`/purchase-requests/${id}/line-items`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
export const deletePurchaseLine = (id: string, lineId: number) =>
  apiFetch<void>(`/purchase-requests/${id}/line-items/${lineId}`, {
    method: "DELETE",
  });
export const validatePurchaseRequest = (id: string) =>
  apiFetch<PurchaseValidation>(`/purchase-requests/${id}/validation`);
export const submitPurchaseRequest = (id: string) =>
  apiFetch<PurchaseRequest>(`/purchase-requests/${id}/submit`, {
    method: "POST",
  });
export const clonePurchaseRequest = (id: string) =>
  apiFetch<PurchaseRequest>(`/purchase-requests/${id}/clone`, {
    method: "POST",
  });
export const listAttachments = (id: string) =>
  apiFetch<Attachment[]>(`/purchase-requests/${id}/attachments`);
export async function uploadAttachment(
  id: string,
  category: string,
  file: File,
): Promise<Attachment> {
  const body = new FormData();
  body.set("category", category);
  body.set("file", file);
  return apiFetch<Attachment>(`/purchase-requests/${id}/attachments`, {
    method: "POST",
    body,
  });
}
export const deleteAttachment = (id: string, attachmentId: string) =>
  apiFetch<void>(`/purchase-requests/${id}/attachments/${attachmentId}`, {
    method: "DELETE",
  });
export const downloadAttachment = (id: string, attachmentId: string) =>
  apiDownload(`/purchase-requests/${id}/attachments/${attachmentId}/content`);
export const getWorkflowInstance = (id: string) =>
  apiFetch<WorkflowInstance>(`/purchase-requests/${id}/workflow`);
export const advanceWorkflow = (instanceId: number, action: string) =>
  apiFetch<WorkflowInstance>(
    `/workflow-engine/instances/${instanceId}/actions`,
    {
      method: "POST",
      body: JSON.stringify({
        action,
        actor: "authenticated-user",
        context_patch: {},
      }),
    },
  );
