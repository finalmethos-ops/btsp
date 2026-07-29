import { apiFetch } from "./api";

export type StoreRecord = {
  id: number;
  store_number: string;
  name: string;
  region_code: string;
  operating_company: string | null;
  entity_code: string | null;
  purchasing_program: string | null;
  regional_manager_name: string | null;
  owner_operator_name: string | null;
  general_manager_name: string | null;
  manager_email: string | null;
  address_line1: string | null;
  city: string | null;
  state_code: string | null;
  postal_code: string | null;
  timezone: string | null;
  is_ordering_enabled: boolean;
  is_active: boolean;
  source_system: string;
  source_updated_at: string | null;
  created_at: string;
  updated_at: string;
};

export type StoreWrite = Omit<StoreRecord, "id" | "created_at" | "updated_at">;

export type StoreImportResult = {
  total_rows: number;
  upserted_rows: number;
  failed_rows: number;
  errors: { row_number: number; store_number: string; message: string }[];
};

export type POStoreFilterOptions = {
  entities: { entity_code: string; regions: string[] }[];
};

export type StoreDirectoryOptions = {
  entities: string[];
  purchasing_programs: string[];
  regions: string[];
  entity_regions: Record<string, string[]>;
};

export type EntityRegion = { entity_code: string; region_code: string };
export const listEntityRegions = () =>
  apiFetch<EntityRegion[]>("/stores/entity-regions");
export const createEntityRegion = (entityCode: string, regionCode: string) =>
  apiFetch<EntityRegion>("/stores/entity-regions", {
    method: "POST",
    body: JSON.stringify({ entity_code: entityCode, region_code: regionCode }),
  });
export const deleteEntityRegion = (entityCode: string, regionCode: string) =>
  apiFetch<void>(
    `/stores/entity-regions/${encodeURIComponent(entityCode)}/${encodeURIComponent(regionCode)}`,
    { method: "DELETE" },
  );

export const getStoreDirectoryOptions = () =>
  apiFetch<StoreDirectoryOptions>("/stores/directory-options");

export const getPOStoreFilterOptions = () =>
  apiFetch<POStoreFilterOptions>("/stores/po-filter-options");

export const listManagedStores = (active?: boolean) =>
  apiFetch<StoreRecord[]>(
    `/stores/management${active === undefined ? "" : `?active=${active}`}`,
  );

export const saveStore = (payload: StoreWrite) =>
  apiFetch<StoreRecord>("/stores/upsert", {
    method: "POST",
    body: JSON.stringify(payload),
  });

export const changeStoreStatus = (storeNumber: string, isActive: boolean) =>
  apiFetch<StoreRecord>(
    `/stores/${encodeURIComponent(storeNumber)}/status?is_active=${isActive}`,
    { method: "PATCH" },
  );

export const importStoreWorkbook = (file: File, authoritative: boolean) => {
  const body = new FormData();
  body.append("workbook", file);
  return apiFetch<StoreImportResult>(
    `/stores/import-workbook?authoritative=${authoritative}`,
    { method: "POST", body },
  );
};
