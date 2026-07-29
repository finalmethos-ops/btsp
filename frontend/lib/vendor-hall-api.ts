import { apiDownload, apiDownloadWithFilename, apiFetch } from "./api";

export type VendorHallBoothStatus =
  | "draft"
  | "inventory_submitted"
  | "ready_for_inspection"
  | "checkin_in_progress"
  | "fully_checked_in"
  | "exceptions_present"
  | "admin_reviewed"
  | "closed";

export type VendorHallItemStatus =
  | "expected"
  | "checked_in"
  | "damaged"
  | "not_in_booth"
  | "quantity_mismatch"
  | "purchased"
  | "removed";

export type VendorHallItemCondition =
  | "new"
  | "floor_model"
  | "open_box"
  | "used"
  | "damaged"
  | "unknown";

export type VendorHallEventWrite = {
  sub_event_id?: string | null;
  status: "draft" | "open" | "closed";
  opens_at?: string | null;
  vendor_submission_deadline?: string | null;
  staff_checkin_opens_at?: string | null;
  staff_checkin_deadline?: string | null;
  allow_vendor_edits_after_submission: boolean;
  require_staff_checkin: boolean;
};

export type VendorHallEvent = VendorHallEventWrite & {
  id: string;
  event_id: string;
  event_name: string;
  sub_event_name: string | null;
  created_at: string;
  updated_at: string;
};

export type VendorHallBooth = {
  id: string;
  vendor_hall_event_id: string;
  event_vendor_booth_id: string | null;
  assigned_staff_membership_id: string | null;
  assigned_staff_display_name: string | null;
  event_id: string;
  event_name: string;
  vendor_code: string;
  vendor_name: string | null;
  booth_number: string;
  booth_name: string;
  floor_map_zone: string | null;
  map_x: string | null;
  map_y: string | null;
  map_width: string | null;
  map_height: string | null;
  map_manually_adjusted: boolean;
  status: VendorHallBoothStatus;
  submitted_at: string | null;
  checkin_started_at: string | null;
  checkin_completed_at: string | null;
  exceptions_count: number;
  available_for_sale_count: number;
  inventory_count: number;
  updated_at: string;
};

export type VendorHallBoothMapPositionWrite = {
  floor_map_zone?: string | null;
  map_x?: string | null;
  map_y?: string | null;
  map_width?: string | null;
  map_height?: string | null;
};

export const assignVendorHallBoothStaff = (
  eventId: string,
  boothId: string,
  membershipId: string | null,
) =>
  apiFetch<VendorHallBooth>(
    `/vendor-hall/events/${eventId}/booths/${boothId}/staff-assignment`,
    {
      method: "PUT",
      body: JSON.stringify({ membership_id: membershipId }),
    },
  );

export type VendorHallSummary = {
  event_id: string;
  event_name: string;
  vendor_hall_event_id: string | null;
  booth_total: number;
  inventory_submitted: number;
  checkin_in_progress: number;
  fully_checked_in: number;
  exceptions_present: number;
  closed: number;
  completion_percentage: string;
  inventory_item_total: number;
  inventory_items_checked: number;
  inventory_completion_percentage: string;
  closeout_ready: boolean;
  vendors_not_submitted: VendorHallBooth[];
};

export type VendorHallInventoryItemWrite = {
  model_number?: string | null;
  serial_number?: string | null;
  item_name: string;
  description?: string | null;
  quantity_expected: number;
  unit_price?: string | null;
  currency: string;
  condition: VendorHallItemCondition;
  status: VendorHallItemStatus;
  available_for_sale: boolean;
  sell_to_buddys_price?: string | null;
  notes?: string | null;
  vendor_notes?: string | null;
};

export type VendorHallInventoryItem = VendorHallInventoryItemWrite & {
  id: string;
  vendor_hall_booth_id: string;
  event_id: string;
  vendor_code: string;
  quantity_checked_in: number;
  staff_notes: string | null;
  validated: boolean;
  attachments: VendorHallItemAttachment[];
  created_at: string;
  updated_at: string;
};

export type VendorHallInventoryImport = {
  id: string;
  vendor_hall_booth_id: string;
  filename: string;
  content_type: string;
  row_count: number;
  accepted_count: number;
  rejected_count: number;
  status: string;
  error_summary: string | null;
  uploaded_by: string;
  uploaded_at: string;
  completed_at: string | null;
};

export type VendorHallItemAttachment = {
  id: string;
  inventory_item_id: string;
  attachment_type: "photo" | "spec_sheet" | "other";
  filename: string;
  content_type: string;
  uploaded_by: string;
  uploaded_at: string;
};

export type VendorHallItemCheckinWrite = {
  status: VendorHallItemStatus;
  quantity_checked: number;
  condition?: VendorHallItemCondition | null;
  damage_notes?: string | null;
  exception_notes?: string | null;
  staff_notes?: string | null;
};

export type VendorHallInventoryStaffUpdate = {
  quantity_checked_in: number;
  condition: VendorHallItemCondition;
  staff_notes?: string | null;
};

export type VendorHallInventorySplitWrite = {
  split_quantity: number;
  status: VendorHallItemStatus;
  notes?: string | null;
};

type VendorHallFloorMapWrite = {
  name: string;
  layout_json: Record<string, unknown>;
  is_active: boolean;
};

export type VendorHallFloorMap = VendorHallFloorMapWrite & {
  id: string;
  vendor_hall_event_id: string;
  has_image: boolean;
  uploaded_by: string;
  uploaded_at: string;
};

export type VendorHallFloorMapStatus = {
  event_id: string;
  event_name: string;
  floor_map: VendorHallFloorMap | null;
  booths: VendorHallBooth[];
};

export type VendorHallDirectoryBooth = Pick<
  VendorHallBooth,
  | "id"
  | "booth_number"
  | "booth_name"
  | "vendor_name"
  | "floor_map_zone"
  | "map_x"
  | "map_y"
  | "map_width"
  | "map_height"
> & { attendees: string[]; is_saved: boolean; is_visited: boolean };

export type VendorHallDirectory = {
  event_id: string;
  event_name: string;
  floor_map: VendorHallFloorMap | null;
  booths: VendorHallDirectoryBooth[];
};

export type VendorHallExportReport =
  | "full-inventory"
  | "available-for-sale"
  | "damaged-items"
  | "missing-items"
  | "vendor-summary"
  | "booth-completion"
  | "staff-checkin-log";

export const configureVendorHall = (
  eventId: string,
  payload: VendorHallEventWrite,
) =>
  apiFetch<VendorHallEvent>(`/vendor-hall/events/${eventId}`, {
    method: "PUT",
    body: JSON.stringify(payload),
  });

export const syncVendorHallBooths = (eventId: string) =>
  apiFetch<VendorHallBooth[]>(`/vendor-hall/events/${eventId}/sync-booths`, {
    method: "POST",
  });

export const listVendorHallBooths = (eventId: string) =>
  apiFetch<VendorHallBooth[]>(`/vendor-hall/events/${eventId}/booths`);

export const getVendorHallSummary = (eventId: string) =>
  apiFetch<VendorHallSummary>(`/vendor-hall/events/${eventId}/summary`);

export async function exportVendorHallReport(
  eventId: string,
  reportType: VendorHallExportReport,
) {
  const download = await apiDownloadWithFilename(
    `/vendor-hall/events/${eventId}/exports/${reportType}`,
  );
  const url = URL.createObjectURL(download.blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download =
    download.filename ?? `vendor-hall-${eventId}-${reportType}.csv`;
  anchor.click();
  URL.revokeObjectURL(url);
}

export const forceCloseVendorHall = (eventId: string) =>
  apiFetch<VendorHallEvent>(`/vendor-hall/events/${eventId}/force-close`, {
    method: "POST",
  });

export async function importVendorHallFloorMapPdf(
  eventId: string,
  name: string,
  file: File,
) {
  const body = new FormData();
  body.set("name", name);
  body.set("file", file);
  return apiFetch<VendorHallFloorMap>(
    `/vendor-hall/events/${eventId}/floor-map/import-pdf`,
    { method: "POST", body },
  );
}

export const getVendorHallFloorMapContent = (eventId: string, render = false) =>
  apiDownload(
    `/vendor-hall/events/${eventId}/floor-map/content${render ? "?render=true" : ""}`,
  );

export const getVendorHallFloorMapStatus = (eventId: string) =>
  apiFetch<VendorHallFloorMapStatus>(
    `/vendor-hall/events/${eventId}/floor-map`,
  );

export const getVendorHallDirectory = (eventId: string) =>
  apiFetch<VendorHallDirectory>(`/vendor-hall/events/${eventId}/directory`);

export const getVendorHallDirectoryContent = (eventId: string) =>
  apiDownload(`/vendor-hall/events/${eventId}/directory/content`);

export const saveVendorHallDirectoryBooth = (
  eventId: string,
  boothId: string,
) =>
  apiFetch<void>(
    `/vendor-hall/events/${eventId}/directory/booths/${boothId}/saved`,
    { method: "POST" },
  );

export const removeVendorHallDirectoryBooth = (
  eventId: string,
  boothId: string,
) =>
  apiFetch<void>(
    `/vendor-hall/events/${eventId}/directory/booths/${boothId}/saved`,
    { method: "DELETE" },
  );

export const setVendorHallDirectoryBoothVisited = (
  eventId: string,
  boothId: string,
  visited: boolean,
) =>
  apiFetch<void>(
    `/vendor-hall/events/${eventId}/directory/booths/${boothId}/visited?visited=${visited}`,
    { method: "PUT" },
  );

export const messageVendorHallDirectoryBooth = (
  eventId: string,
  boothId: string,
  payload: { subject: string; body: string },
) =>
  apiFetch<{ sent_count: number }>(
    `/vendor-hall/events/${eventId}/directory/booths/${boothId}/messages`,
    { method: "POST", body: JSON.stringify(payload) },
  );

export const updateVendorHallBoothMapPosition = (
  eventId: string,
  boothId: string,
  payload: VendorHallBoothMapPositionWrite,
) =>
  apiFetch<VendorHallBooth>(
    `/vendor-hall/events/${eventId}/booths/${boothId}/map-position`,
    {
      method: "PUT",
      body: JSON.stringify(payload),
    },
  );

export const listMyVendorHallBooths = () =>
  apiFetch<VendorHallBooth[]>("/vendor-hall/mine");

export const listVendorHallInventory = (boothId: string) =>
  apiFetch<VendorHallInventoryItem[]>(
    `/vendor-hall/booths/${boothId}/inventory`,
  );

export const createVendorHallInventoryItem = (
  boothId: string,
  payload: VendorHallInventoryItemWrite,
) =>
  apiFetch<VendorHallInventoryItem>(
    `/vendor-hall/booths/${boothId}/inventory`,
    {
      method: "POST",
      body: JSON.stringify(payload),
    },
  );

export const importVendorHallInventory = (boothId: string, file: File) => {
  const body = new FormData();
  body.append("file", file);
  return apiFetch<VendorHallInventoryImport>(
    `/vendor-hall/booths/${boothId}/inventory/import`,
    {
      method: "POST",
      body,
    },
  );
};

export const updateVendorHallInventoryItem = (
  boothId: string,
  itemId: string,
  payload: VendorHallInventoryItemWrite,
) =>
  apiFetch<VendorHallInventoryItem>(
    `/vendor-hall/booths/${boothId}/inventory/${itemId}`,
    {
      method: "PUT",
      body: JSON.stringify(payload),
    },
  );

export const splitVendorHallInventoryItem = (
  boothId: string,
  itemId: string,
  payload: VendorHallInventorySplitWrite,
) =>
  apiFetch<VendorHallInventoryItem>(
    `/vendor-hall/booths/${boothId}/inventory/${itemId}/split`,
    {
      method: "POST",
      body: JSON.stringify(payload),
    },
  );

export const uploadVendorHallItemAttachment = (
  boothId: string,
  itemId: string,
  attachmentType: "photo" | "spec_sheet" | "other",
  file: File,
) => {
  const body = new FormData();
  body.append("file", file);
  return apiFetch<VendorHallItemAttachment>(
    `/vendor-hall/booths/${boothId}/inventory/${itemId}/attachments?attachment_type=${attachmentType}`,
    {
      method: "POST",
      body,
    },
  );
};

export const downloadVendorHallItemAttachment = (
  boothId: string,
  itemId: string,
  attachmentId: string,
) =>
  apiDownloadWithFilename(
    `/vendor-hall/booths/${boothId}/inventory/${itemId}/attachments/${attachmentId}/content`,
  );

export const deleteVendorHallItemAttachment = (
  boothId: string,
  itemId: string,
  attachmentId: string,
) =>
  apiFetch<void>(
    `/vendor-hall/booths/${boothId}/inventory/${itemId}/attachments/${attachmentId}`,
    { method: "DELETE" },
  );

export const submitVendorHallInventory = (boothId: string) =>
  apiFetch<VendorHallBooth>(`/vendor-hall/booths/${boothId}/submit`, {
    method: "POST",
  });

export const markVendorHallBoothReadyForInspection = (boothId: string) =>
  apiFetch<VendorHallBooth>(
    `/vendor-hall/booths/${boothId}/ready-for-inspection`,
    {
      method: "POST",
    },
  );

export const startVendorHallBoothCheckin = (
  boothId: string,
  notes?: string | null,
) =>
  apiFetch(`/vendor-hall/booths/${boothId}/checkin/start`, {
    method: "POST",
    body: JSON.stringify({ notes: notes ?? null }),
  });

export const checkinVendorHallInventoryItem = (
  boothId: string,
  itemId: string,
  payload: VendorHallItemCheckinWrite,
) =>
  apiFetch(`/vendor-hall/booths/${boothId}/inventory/${itemId}/checkin`, {
    method: "POST",
    body: JSON.stringify(payload),
  });

export const updateVendorHallInventoryItemStaff = (
  boothId: string,
  itemId: string,
  payload: VendorHallInventoryStaffUpdate,
) =>
  apiFetch<VendorHallInventoryItem>(
    `/vendor-hall/booths/${boothId}/inventory/${itemId}/staff-update`,
    { method: "PUT", body: JSON.stringify(payload) },
  );

export const completeVendorHallBoothCheckin = (
  boothId: string,
  notes?: string | null,
) =>
  apiFetch<VendorHallBooth>(`/vendor-hall/booths/${boothId}/checkin/complete`, {
    method: "POST",
    body: JSON.stringify({ notes: notes ?? null }),
  });
