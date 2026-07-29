import { apiDownloadWithFilename, apiFetch } from "./api";

export type EventSettlementStatus =
  | "draft"
  | "collecting_evidence"
  | "exceptions_present"
  | "ready_for_review"
  | "approved"
  | "closed";

export type EventSettlementException = {
  id: string;
  exception_type: string;
  severity: string;
  status: string;
  reference_type: string | null;
  reference_id: string | null;
  description: string;
  created_at: string;
  resolved_by: string | null;
  resolved_at: string | null;
  resolution_notes: string | null;
};

export type EventSettlementSummary = {
  event_id: string;
  event_name: string;
  settlement_event_id: string | null;
  status: EventSettlementStatus;
  vendor_hall_status: string | null;
  vendor_hall_closeout_ready: boolean | null;
  order_total: number;
  order_released: number;
  approved_units: number;
  approved_spend: string;
  loadout_assignment_total: number;
  loadout_signed: number;
  loadout_released: number;
  loadout_exception_assignments: number;
  loadout_final_review_pending: number;
  ordered_not_loaded_count: number;
  loaded_not_ordered_count: number;
  quantity_mismatch_count: number;
  open_exception_count: number;
  readiness_percentage: number | string;
  exceptions: EventSettlementException[];
  notes: string | null;
  approved_at: string | null;
  approved_by: string | null;
  closed_at: string | null;
  closed_by: string | null;
  updated_at: string | null;
};

export type EventSettlementWrite = {
  status: EventSettlementStatus;
  notes?: string | null;
};

export type EventSettlementExceptionWrite = {
  exception_type: string;
  severity: string;
  reference_type?: string | null;
  reference_id?: string | null;
  description: string;
};

export type EventSettlementExceptionResolutionWrite = {
  resolution_notes?: string | null;
};

export type EventSettlementExportReport =
  | "summary"
  | "closeout-packet"
  | "reconciliation-detail"
  | "exceptions"
  | "order-closeout"
  | "loadout-closeout"
  | "feedback"
  | "audit-log";

export const getEventSettlementSummary = (eventId: string) =>
  apiFetch<EventSettlementSummary>(
    `/event-settlement/events/${eventId}/summary`,
  );

export const configureEventSettlement = (
  eventId: string,
  payload: EventSettlementWrite,
) =>
  apiFetch<EventSettlementSummary>(`/event-settlement/events/${eventId}`, {
    method: "PUT",
    body: JSON.stringify(payload),
  });

export const createEventSettlementException = (
  eventId: string,
  payload: EventSettlementExceptionWrite,
) =>
  apiFetch<EventSettlementSummary>(
    `/event-settlement/events/${eventId}/exceptions`,
    {
      method: "POST",
      body: JSON.stringify(payload),
    },
  );

export const resolveEventSettlementException = (
  exceptionId: string,
  payload: EventSettlementExceptionResolutionWrite,
) =>
  apiFetch<EventSettlementSummary>(
    `/event-settlement/exceptions/${exceptionId}/resolve`,
    {
      method: "POST",
      body: JSON.stringify(payload),
    },
  );

export const reopenEventSettlementException = (exceptionId: string) =>
  apiFetch<EventSettlementSummary>(
    `/event-settlement/exceptions/${exceptionId}/reopen`,
    {
      method: "POST",
    },
  );

export async function exportEventSettlementReport(
  eventId: string,
  reportType: EventSettlementExportReport,
) {
  const download = await apiDownloadWithFilename(
    `/event-settlement/events/${eventId}/exports/${reportType}`,
  );
  const url = URL.createObjectURL(download.blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download =
    download.filename ?? `event-settlement-${eventId}-${reportType}.csv`;
  anchor.click();
  URL.revokeObjectURL(url);
}
