import { apiDownload, apiFetch } from "@/lib/api";

export type OperationalDashboard = {
  purchasing: {
    purchase_order_count: number;
    purchase_order_statuses: Array<{ status: string; count: number }>;
    ordered_spend: Array<{ currency: string; amount: string }>;
  };
  receiving: {
    receipt_count: number;
    accepted_quantity: string;
    rejected_quantity: string;
    open_variance_count: number;
    open_backorder_count: number;
    outstanding_backorder_quantity: string;
  };
  invoices: {
    invoice_count: number;
    invoice_statuses: Array<{ status: string; count: number }>;
    invoiced_amount: Array<{ currency: string; amount: string }>;
    line_match_exception_count: number;
  };
  reconciliation: {
    case_count: number;
    case_statuses: Array<{ status: string; count: number }>;
    open_exception_count: number;
  };
};

export type SpendDimension =
  | "vendor"
  | "store"
  | "workflow"
  | "category"
  | "month";
export type SpendAnalysis = {
  group_by: SpendDimension;
  metrics: Array<{
    dimension_key: string;
    currency: string;
    purchase_order_count: number;
    line_count: number;
    quantity: string;
    amount: string;
  }>;
};

export type VendorScorecard = {
  vendor_code: string;
  vendor_name: string;
  purchase_order_count: number;
  acknowledgement_coverage_rate: string | null;
  on_time_delivery_rate: string | null;
  receiving_acceptance_rate: string | null;
  invoice_match_rate: string | null;
  approved_reconciliation_count: number;
  rejected_reconciliation_count: number;
};

export type WorkflowMetric = {
  workflow_code: string;
  instance_count: number;
  active_count: number;
  completed_count: number;
  current_states: Array<{ status: string; count: number }>;
  transition_count: number;
  approval_count: number;
  rejection_count: number;
  average_completion_seconds: string | null;
  median_completion_seconds: string | null;
  p90_completion_seconds: string | null;
  approval_actors: Array<{
    actor: string;
    approval_count: number;
    rejection_count: number;
  }>;
};

export type InventoryPosition = {
  store_number: string;
  product_code: string;
  product_name: string;
  accepted_quantity: string;
  rejected_quantity: string;
  outstanding_backorder_quantity: string;
};

export type ReportSchedule = {
  id: string;
  name: string;
  report_type: string;
  interval_minutes: number;
  next_run_at: string;
  is_enabled: boolean;
};

export type ReportRun = {
  id: string;
  schedule_id: string;
  status: string;
  size_bytes: number | null;
  sha256: string | null;
  error_message: string | null;
  created_at: string;
};

export const getOperationalDashboard = () =>
  apiFetch<OperationalDashboard>("/analytics/operational-dashboard");

export const getSpendAnalysis = (groupBy: SpendDimension) =>
  apiFetch<SpendAnalysis>(
    `/analytics/spend?group_by=${encodeURIComponent(groupBy)}`,
  );

export const getVendorScorecards = () =>
  apiFetch<{ scorecards: VendorScorecard[] }>("/analytics/vendor-scorecards");

export const getWorkflowAnalytics = () =>
  apiFetch<{ workflows: WorkflowMetric[] }>("/analytics/workflows");

export const getInventoryPositions = () =>
  apiFetch<{ positions: InventoryPosition[] }>("/analytics/inventory-position");
export const listReportSchedules = () =>
  apiFetch<ReportSchedule[]>("/analytics/report-schedules");
export const listReportRuns = () =>
  apiFetch<ReportRun[]>("/analytics/report-runs");
export const createReportSchedule = (payload: Record<string, unknown>) =>
  apiFetch<ReportSchedule>("/analytics/report-schedules", {
    method: "POST",
    body: JSON.stringify(payload),
  });
export const runDueReports = () =>
  apiFetch<ReportRun[]>("/analytics/report-runs/run-due", { method: "POST" });
export const downloadAnalyticsExport = (reportType: string) =>
  apiDownload(`/analytics/exports/${encodeURIComponent(reportType)}`);
export const downloadReportRun = (runId: string) =>
  apiDownload(`/analytics/report-runs/${encodeURIComponent(runId)}/content`);
