import { apiDownload, apiFetch } from "./api";

export type VendorModel = {
  product_code: string;
  model_identifier: string;
  vendor_code: string;
  name: string;
  model_number: string | null;
  department: string | null;
  product_category_code: string | null;
  brand: string | null;
  is_clump: boolean;
  part_of_clump: boolean;
  cost_effective_start_date: string | null;
  cost_status: string;
  unit_price: string;
  currency: string;
  minimum_order_quantity: string;
  moq_rule_id: number | null;
  is_available: boolean;
  is_active: boolean;
};

export type ModelCategory = {
  id: number;
  department: string;
  product_category_code: string;
  status: string;
};

export const listModelCategories = () =>
  apiFetch<ModelCategory[]>("/catalog/model-categories");

export type VendorMOQRule = {
  id: number;
  code: string;
  name: string;
  threshold_type: "unit_quantity" | "order_amount";
  threshold_value: string;
  is_active: boolean;
  contributor_rule_ids: number[];
};

export const listVendorMOQRules = () =>
  apiFetch<VendorMOQRule[]>("/vendor-profile/moq-rules");

export const saveVendorMOQRule = (rule: {
  id?: number;
  code: string;
  name: string;
  threshold_type: "unit_quantity" | "order_amount";
  threshold_value: number;
  is_active: boolean;
}) =>
  apiFetch<VendorMOQRule>(
    rule.id
      ? `/vendor-profile/moq-rules/${rule.id}`
      : "/vendor-profile/moq-rules",
    {
      method: rule.id ? "PUT" : "POST",
      body: JSON.stringify(rule),
    },
  );

export const setMOQContributors = (
  ruleId: number,
  contributor_rule_ids: number[],
) =>
  apiFetch<void>(`/vendor-profile/moq-rules/${ruleId}/contributors`, {
    method: "PUT",
    body: JSON.stringify({ contributor_rule_ids }),
  });

export const getVendorStateExclusions = () =>
  apiFetch<{ state_codes: string[] }>("/vendor-profile/state-exclusions");

export const saveVendorStateExclusions = (state_codes: string[]) =>
  apiFetch<{ state_codes: string[] }>("/vendor-profile/state-exclusions", {
    method: "PUT",
    body: JSON.stringify({ state_codes }),
  });

export const getVendorPOEmailPreference = () =>
  apiFetch<{ po_email_recipient: string | null }>(
    "/vendor-profile/po-email-preference",
  );

export const saveVendorPOEmailPreference = (
  po_email_recipient: string | null,
) =>
  apiFetch<{ po_email_recipient: string | null }>(
    "/vendor-profile/po-email-preference",
    {
      method: "PUT",
      body: JSON.stringify({ po_email_recipient }),
    },
  );

export type VendorModelCost = {
  id: number;
  product_code: string;
  vendor_code: string;
  unit_price: string;
  currency: string;
  effective_from: string;
  effective_to: string | null;
  changed_by: string;
  source: string;
};

export type VendorModelImportResult = {
  filename: string;
  created: number;
  updated: number;
  unchanged: number;
  total_rows: number;
};

export type VendorModelClassification =
  | "all"
  | "clump"
  | "part_of_clump"
  | "single_item";

export const listVendorModels = (
  search = "",
  classification: VendorModelClassification = "all",
) => {
  const params = new URLSearchParams({ classification });
  if (search) params.set("search", search);
  return apiFetch<VendorModel[]>(`/vendor-models?${params}`);
};

export const updateVendorModel = (
  productCode: string,
  payload: Record<string, unknown>,
) =>
  apiFetch<VendorModel>(`/vendor-models/${encodeURIComponent(productCode)}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });

export const getVendorModelCostHistory = (productCode: string) =>
  apiFetch<VendorModelCost[]>(
    `/vendor-models/${encodeURIComponent(productCode)}/cost-history`,
  );

export async function importVendorModels(
  file: File,
): Promise<VendorModelImportResult> {
  const body = new FormData();
  body.set("file", file);
  return apiFetch<VendorModelImportResult>("/vendor-models/import", {
    method: "POST",
    body,
  });
}

export async function exportVendorModels(): Promise<void> {
  const blob = await apiDownload("/vendor-models/export/models.xlsx");
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = "vendor-models.xlsx";
  anchor.click();
  URL.revokeObjectURL(url);
}
