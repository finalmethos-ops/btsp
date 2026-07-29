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

export type ExecutiveEntitySpendMetric = {
  entity_code: string;
  currency: string;
  amount: string;
};

export type ExecutiveBestSellerMetric = {
  rank: number;
  product_code: string;
  product_name: string;
  currency: string;
  quantity: string;
  amount: string;
};

export type ExecutiveSpendDashboard = {
  as_of: string;
  month_start: string;
  year_start: string;
  mtd_by_entity: ExecutiveEntitySpendMetric[];
  ytd_by_entity: ExecutiveEntitySpendMetric[];
  top_sellers_mtd: ExecutiveBestSellerMetric[];
};

export type SpendDimension =
  | "vendor"
  | "store"
  | "workflow"
  | "department"
  | "product_code"
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
  ordered_spend: Array<{ currency: string; amount: string }>;
  acknowledgement_coverage_rate: string | null;
  on_time_delivery_rate: string | null;
  receiving_acceptance_rate: string | null;
  invoice_match_rate: string | null;
  approved_reconciliation_count: number;
  rejected_reconciliation_count: number;
  vendor_fulfillment_event_count: number;
  delay_event_count: number;
  backorder_event_count: number;
  out_of_stock_event_count: number;
  substitution_event_count: number;
  confirmed_po_change_count: number;
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
  content_type: string | null;
  size_bytes: number | null;
  sha256: string | null;
  error_message: string | null;
  created_at: string;
};

export const getOperationalDashboard = () =>
  apiFetch<OperationalDashboard>("/analytics/operational-dashboard");

export const getExecutiveSpendDashboard = () =>
  apiFetch<ExecutiveSpendDashboard>("/analytics/executive-spend-dashboard");

export type SpendFilters = {
  dateFrom?: string;
  dateTo?: string;
  vendorCode?: string;
  storeNumber?: string;
  workflowCode?: string;
};

export const getSpendAnalysis = (
  groupBy: SpendDimension,
  filters: SpendFilters = {},
) => {
  const params = new URLSearchParams({ group_by: groupBy });
  if (filters.dateFrom)
    params.set("date_from", `${filters.dateFrom}T00:00:00Z`);
  if (filters.dateTo) params.set("date_to", `${filters.dateTo}T23:59:59Z`);
  if (filters.vendorCode) params.set("vendor_code", filters.vendorCode);
  if (filters.storeNumber) params.set("store_number", filters.storeNumber);
  if (filters.workflowCode) params.set("workflow_code", filters.workflowCode);
  return apiFetch<SpendAnalysis>(`/analytics/spend?${params.toString()}`);
};

export const getVendorScorecards = (
  filters: {
    dateFrom?: string;
    dateTo?: string;
    minimumOrders?: number;
  } = {},
) => {
  const params = new URLSearchParams();
  if (filters.dateFrom)
    params.set("date_from", `${filters.dateFrom}T00:00:00Z`);
  if (filters.dateTo) params.set("date_to", `${filters.dateTo}T23:59:59Z`);
  if (filters.minimumOrders && filters.minimumOrders > 1) {
    params.set("minimum_orders", String(filters.minimumOrders));
  }
  const query = params.toString();
  return apiFetch<{ scorecards: VendorScorecard[] }>(
    `/analytics/vendor-scorecards${query ? `?${query}` : ""}`,
  );
};

export const getWorkflowAnalytics = (
  filters: {
    dateFrom?: string;
    dateTo?: string;
    workflowCode?: string;
  } = {},
) => {
  const params = new URLSearchParams();
  if (filters.dateFrom)
    params.set("date_from", `${filters.dateFrom}T00:00:00Z`);
  if (filters.dateTo) params.set("date_to", `${filters.dateTo}T23:59:59Z`);
  if (filters.workflowCode) params.set("workflow_code", filters.workflowCode);
  const query = params.toString();
  return apiFetch<{ workflows: WorkflowMetric[] }>(
    `/analytics/workflows${query ? `?${query}` : ""}`,
  );
};

export const getInventoryPositions = (
  filters: {
    storeNumber?: string;
    productCode?: string;
  } = {},
) => {
  const params = new URLSearchParams();
  if (filters.storeNumber) params.set("store_number", filters.storeNumber);
  if (filters.productCode) params.set("product_code", filters.productCode);
  const query = params.toString();
  return apiFetch<{ positions: InventoryPosition[] }>(
    `/analytics/inventory-position${query ? `?${query}` : ""}`,
  );
};
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
export const downloadAnalyticsExport = (
  reportType: string,
  filters: Record<string, string | number | undefined> = {},
) => {
  const params = new URLSearchParams();
  Object.entries(filters).forEach(([key, value]) => {
    if (value !== undefined && value !== "") params.set(key, String(value));
  });
  const query = params.toString();
  return apiDownload(
    `/analytics/exports/${encodeURIComponent(reportType)}${query ? `?${query}` : ""}`,
  );
};
export const downloadReportRun = (runId: string) =>
  apiDownload(`/analytics/report-runs/${encodeURIComponent(runId)}/content`);
