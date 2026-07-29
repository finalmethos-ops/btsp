import { apiFetch } from "./api";
import { VendorModel, VendorModelCost } from "./vendor-model-api";
import { VendorModelClassification } from "./vendor-model-api";

export const searchModelCatalog = (
  search = "",
  vendorCode = "",
  department = "",
  productCategoryCode = "",
  classification: VendorModelClassification = "all",
) => {
  const params = new URLSearchParams({ limit: "2000", classification });
  if (search) params.set("search", search);
  if (vendorCode) params.set("vendor_code", vendorCode);
  if (department) params.set("department", department);
  if (productCategoryCode)
    params.set("product_category_code", productCategoryCode);
  return apiFetch<VendorModel[]>(`/model-catalog?${params}`);
};

export const getModelCatalogCostHistory = (productCode: string) =>
  apiFetch<VendorModelCost[]>(
    `/model-catalog/${encodeURIComponent(productCode)}/cost-history`,
  );
