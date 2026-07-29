import { apiDownloadWithFilename, apiFetch } from "./api";

export type StoreLoadoutAssignmentStatus =
  | "not_started"
  | "in_progress"
  | "exceptions_present"
  | "ready_for_final_review"
  | "signed_complete"
  | "released_from_venue";

export type StoreLoadoutItemStatus =
  | "assigned"
  | "found"
  | "damaged"
  | "missing"
  | "quantity_mismatch"
  | "substituted"
  | "removed"
  | "signed_off";

export type StoreLoadoutItem = {
  id: string;
  assignment_id: string;
  event_id: string;
  vendor_hall_booth_id: string;
  vendor_hall_inventory_item_id: string;
  vendor_code: string;
  vendor_name: string | null;
  booth_number: string;
  item_name: string;
  model_number: string | null;
  serial_number: string | null;
  quantity_assigned: number;
  quantity_found: number;
  condition: string;
  status: StoreLoadoutItemStatus;
  notes: string | null;
  damage_notes: string | null;
  missing_notes: string | null;
  vehicle_label: string | null;
  updated_at: string;
};

export type StoreLoadoutAssignment = {
  id: string;
  store_loadout_event_id: string;
  event_id: string;
  event_name: string;
  store_number: string;
  store_name: string | null;
  store_manager_name: string | null;
  store_manager_email: string | null;
  store_phone: string | null;
  store_address: string | null;
  entity_code: string | null;
  status: StoreLoadoutAssignmentStatus;
  pickup_priority: number;
  loadout_zone: string | null;
  distance_miles: number | null;
  estimated_drive_minutes: number | null;
  recommended_departure_at: string | null;
  notes: string | null;
  team_name: string | null;
  team_member_emails: string[];
  team_lead_emails: string[];
  vehicle_labels: string[];
  vehicle_statuses: Record<string, string>;
  final_review_requested_at: string | null;
  final_review_requested_by: string | null;
  final_review_completed_at: string | null;
  final_review_completed_by: string | null;
  final_review_notes: string | null;
  item_count: number;
  exception_count: number;
  signed_at: string | null;
  signed_by: string | null;
  released_at: string | null;
  released_by: string | null;
  updated_at: string;
  items: StoreLoadoutItem[];
};

export type StoreLoadoutEvent = {
  id: string;
  event_id: string;
  event_name: string;
  status: "draft" | "open" | "closed";
  opens_at: string | null;
  loadout_deadline: string | null;
  default_loadout_zone: string | null;
  venue_departure_notes: string | null;
  dock_master_email: string | null;
  completed_at: string | null;
  created_at: string;
  updated_at: string;
};

export type StoreLoadoutEventWrite = {
  status: "draft" | "open" | "closed";
  opens_at?: string | null;
  loadout_deadline?: string | null;
  default_loadout_zone?: string | null;
  venue_departure_notes?: string | null;
  dock_master_email?: string | null;
};

export type StoreLoadoutRouteEstimate = {
  store_number: string;
  distance_miles: number;
  estimated_drive_minutes: number;
  recommended_departure_at: string;
  arrival_target_at: string;
  source: string;
};

export const estimateStoreLoadoutRoute = (
  eventId: string,
  storeNumber: string,
) =>
  apiFetch<StoreLoadoutRouteEstimate>(
    `/store-loadout/events/${encodeURIComponent(eventId)}/route-estimate/${encodeURIComponent(storeNumber)}`,
  );

export const recalculateStoreLoadoutRoutes = (eventId: string) =>
  apiFetch<{ updated: number; failed_store_numbers: string[] }>(
    `/store-loadout/events/${encodeURIComponent(eventId)}/route-estimates/recalculate`,
    { method: "POST" },
  );

export const uploadStoreLoadoutItemEvidence = (
  assignmentId: string,
  itemId: string,
  file: File,
) => {
  const body = new FormData();
  body.append("file", file);
  return apiFetch<{
    id: string;
    assignment_id: string;
    loadout_item_id: string;
    attachment_type: "photo" | "other";
    filename: string;
    content_type: string;
    uploaded_by: string;
    created_at: string;
  }>(
    `/store-loadout/assignments/${encodeURIComponent(assignmentId)}/items/${encodeURIComponent(itemId)}/attachments`,
    { method: "POST", body },
  );
};

export type StoreLoadoutItemAssignmentWrite = {
  vendor_hall_inventory_item_id: string;
  quantity_assigned: number;
  vehicle_label?: string | null;
  notes?: string | null;
};

export type StoreLoadoutAssignmentWrite = {
  store_number: string;
  entity_code?: string | null;
  pickup_priority: number;
  loadout_zone?: string | null;
  distance_miles?: number | null;
  estimated_drive_minutes?: number | null;
  recommended_departure_at?: string | null;
  notes?: string | null;
  vehicle_labels?: string[];
  items: StoreLoadoutItemAssignmentWrite[];
};

export type StoreLoadoutReassignmentWrite = {
  vehicle_labels?: string[];
  notes?: string | null;
  items: StoreLoadoutItemAssignmentWrite[];
};

export type StoreLoadoutTeamWrite = {
  team_name?: string | null;
  team_member_emails: string[];
  team_lead_emails: string[];
  vehicle_labels: string[];
};

export type StoreLoadoutFinalReviewWrite = {
  notes?: string | null;
};

export type StoreLoadoutSummary = {
  event_id: string;
  event_name: string;
  store_loadout_event_id: string | null;
  assignment_total: number;
  not_started: number;
  in_progress: number;
  exceptions_present: number;
  ready_for_final_review: number;
  signed_complete: number;
  released_from_venue: number;
  item_total: number;
  items_found: number;
  items_damaged: number;
  items_missing: number;
  completion_percentage: number;
  teams: StoreLoadoutTeamSummary[];
};

export type StoreLoadoutTeamSummary = {
  team_name: string;
  status: string;
  assignment_total: number;
  reviewed: number;
  signed: number;
  released: number;
  completion_percentage: number;
};

export type StoreLoadoutItemCheckinWrite = {
  status: StoreLoadoutItemStatus;
  quantity_found: number;
  damage_notes?: string | null;
  missing_notes?: string | null;
};

export type StoreLoadoutSignoffWrite = {
  signer_name: string;
  signer_email: string;
  signature_text: string;
  exception_summary?: string | null;
};

export type StoreLoadoutExportReport =
  | "master"
  | "packing-lists"
  | "damaged-items"
  | "missing-items"
  | "departure-schedule"
  | "audit-log";

export const listMyStoreLoadoutAssignments = () =>
  apiFetch<StoreLoadoutAssignment[]>("/store-loadout/mine");

export const configureStoreLoadoutEvent = (
  eventId: string,
  payload: StoreLoadoutEventWrite,
) =>
  apiFetch<StoreLoadoutEvent>(`/store-loadout/events/${eventId}`, {
    method: "PUT",
    body: JSON.stringify(payload),
  });

export const listStoreLoadoutAssignments = (eventId: string) =>
  apiFetch<StoreLoadoutAssignment[]>(
    `/store-loadout/events/${eventId}/assignments`,
  );

export const autoOrderStoreLoadout = (eventId: string) =>
  apiFetch<StoreLoadoutAssignment[]>(
    `/store-loadout/events/${eventId}/auto-order`,
    { method: "POST" },
  );

export const createStoreLoadoutAssignment = (
  eventId: string,
  payload: StoreLoadoutAssignmentWrite,
) =>
  apiFetch<StoreLoadoutAssignment>(
    `/store-loadout/events/${eventId}/assignments`,
    {
      method: "POST",
      body: JSON.stringify(payload),
    },
  );

export const reassignStoreLoadoutInventory = (
  assignmentId: string,
  payload: StoreLoadoutReassignmentWrite,
) =>
  apiFetch<StoreLoadoutAssignment>(
    `/store-loadout/assignments/${assignmentId}/reassign`,
    { method: "PUT", body: JSON.stringify(payload) },
  );

export const getStoreLoadoutSummary = (eventId: string) =>
  apiFetch<StoreLoadoutSummary>(`/store-loadout/events/${eventId}/summary`);

export const checkinStoreLoadoutItem = (
  assignmentId: string,
  itemId: string,
  payload: StoreLoadoutItemCheckinWrite,
) =>
  apiFetch<StoreLoadoutAssignment>(
    `/store-loadout/assignments/${assignmentId}/items/${itemId}/checkin`,
    {
      method: "POST",
      body: JSON.stringify(payload),
    },
  );

export const markStoreLoadoutAssignmentReady = (assignmentId: string) =>
  apiFetch<StoreLoadoutAssignment>(
    `/store-loadout/assignments/${assignmentId}/ready`,
    {
      method: "POST",
    },
  );

export const assignStoreLoadoutTeam = (
  assignmentId: string,
  payload: StoreLoadoutTeamWrite,
) =>
  apiFetch<StoreLoadoutAssignment>(
    `/store-loadout/assignments/${assignmentId}/team`,
    {
      method: "PUT",
      body: JSON.stringify(payload),
    },
  );

export const completeStoreLoadoutFinalReview = (
  assignmentId: string,
  payload: StoreLoadoutFinalReviewWrite,
) =>
  apiFetch<StoreLoadoutAssignment>(
    `/store-loadout/assignments/${assignmentId}/final-review`,
    {
      method: "POST",
      body: JSON.stringify(payload),
    },
  );

export const signStoreLoadoutAssignment = (
  assignmentId: string,
  payload: StoreLoadoutSignoffWrite,
) =>
  apiFetch<StoreLoadoutAssignment>(
    `/store-loadout/assignments/${assignmentId}/sign`,
    {
      method: "POST",
      body: JSON.stringify(payload),
    },
  );

export const releaseStoreLoadoutAssignment = (assignmentId: string) =>
  apiFetch<StoreLoadoutAssignment>(
    `/store-loadout/assignments/${assignmentId}/release`,
    {
      method: "POST",
    },
  );

export const updateStoreLoadoutVehicleStatus = (
  assignmentId: string,
  vehicleLabel: string,
  status: "expected" | "loading" | "loaded" | "departed",
) =>
  apiFetch<StoreLoadoutAssignment>(
    `/store-loadout/assignments/${assignmentId}/vehicles/${encodeURIComponent(vehicleLabel)}/status`,
    { method: "PUT", body: JSON.stringify({ status }) },
  );

export async function exportStoreLoadoutReport(
  eventId: string,
  reportType: StoreLoadoutExportReport,
) {
  const download = await apiDownloadWithFilename(
    `/store-loadout/events/${eventId}/exports/${reportType}`,
  );
  const url = URL.createObjectURL(download.blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download =
    download.filename ?? `store-loadout-${eventId}-${reportType}.csv`;
  anchor.click();
  URL.revokeObjectURL(url);
}

export async function exportStoreLoadoutPackingListsPdf(eventId: string) {
  const download = await apiDownloadWithFilename(
    `/store-loadout/events/${eventId}/packing-lists-pdf`,
  );
  const url = URL.createObjectURL(download.blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download =
    download.filename ?? `store-loadout-${eventId}-packing-lists.pdf`;
  anchor.click();
  URL.revokeObjectURL(url);
}

export async function exportStoreLoadoutPackingListPdf(
  eventId: string,
  assignmentId: string,
) {
  const download = await apiDownloadWithFilename(
    `/store-loadout/events/${eventId}/assignments/${assignmentId}/packing-list-pdf`,
  );
  const url = URL.createObjectURL(download.blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = download.filename ?? `store-loadout-${assignmentId}.pdf`;
  anchor.click();
  URL.revokeObjectURL(url);
}
