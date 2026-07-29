"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";
import {
  createReportSchedule,
  downloadAnalyticsExport,
  downloadReportRun,
  getInventoryPositions,
  getOperationalDashboard,
  getSpendAnalysis,
  getVendorScorecards,
  getWorkflowAnalytics,
  InventoryPosition,
  listReportRuns,
  listReportSchedules,
  OperationalDashboard,
  SpendAnalysis,
  SpendDimension,
  SpendFilters,
  ReportRun,
  ReportSchedule,
  runDueReports,
  VendorScorecard,
  WorkflowMetric,
} from "@/lib/analytics-api";
import { useAuth } from "@/lib/auth";

function StatusList({
  items,
}: {
  items: Array<{ status: string; count: number }>;
}) {
  if (!items.length)
    return <p className="mt-3 text-sm text-slate-500">No activity yet.</p>;
  return (
    <div className="mt-3 space-y-2">
      {items.map((item) => (
        <div className="flex justify-between text-sm" key={item.status}>
          <span className="capitalize text-slate-600">
            {item.status.replaceAll("_", " ")}
          </span>
          <span className="font-medium">{item.count}</span>
        </div>
      ))}
    </div>
  );
}

export type AnalyticsDashboardMode = "executive" | "vendor" | "reports";

const reportExports = [
  {
    description:
      "One leadership-ready workbook containing every executive analytics view.",
    filename: "btsp-executive-report-pack.xlsx",
    label: "Complete executive report pack",
    parameters: {},
    reportType: "executive_pack",
  },
  {
    description: "Purchase-order quantity and landed spend ranked by vendor.",
    filename: "spend-by-vendor.xlsx",
    label: "Spend by vendor",
    parameters: { group_by: "vendor" },
    reportType: "spend",
  },
  {
    description:
      "Purchase-order quantity and landed spend ranked by department.",
    filename: "spend-by-department.xlsx",
    label: "Spend by department",
    parameters: { group_by: "department" },
    reportType: "spend",
  },
  {
    description: "Best-selling ordered models ranked by actual product code.",
    filename: "spend-by-product-code.xlsx",
    label: "Product performance",
    parameters: { group_by: "product_code" },
    reportType: "spend",
  },
  {
    description:
      "Vendor acknowledgement, delivery, receiving, and exception measures.",
    filename: "vendor-scorecards.xlsx",
    label: "Vendor scorecards",
    parameters: {},
    reportType: "vendor_scorecards",
  },
  {
    description:
      "Workflow throughput, approval outcomes, and completion timing.",
    filename: "workflow-performance.xlsx",
    label: "Workflow performance",
    parameters: {},
    reportType: "workflows",
  },
] as const;

export function AnalyticsDashboard({
  mode = "executive",
}: {
  mode?: AnalyticsDashboardMode;
}) {
  const { user } = useAuth();
  const [dashboard, setDashboard] = useState<OperationalDashboard | null>(null);
  const [spend, setSpend] = useState<SpendAnalysis | null>(null);
  const [spendDimension, setSpendDimension] =
    useState<SpendDimension>("vendor");
  const [spendFilters, setSpendFilters] = useState<SpendFilters>({});
  const [spendFilterDraft, setSpendFilterDraft] = useState<SpendFilters>({});
  const [scorecards, setScorecards] = useState<VendorScorecard[]>([]);
  const [scorecardFilters, setScorecardFilters] = useState({
    dateFrom: "",
    dateTo: "",
    minimumOrders: 1,
  });
  const [workflowMetrics, setWorkflowMetrics] = useState<WorkflowMetric[]>([]);
  const [workflowFilters, setWorkflowFilters] = useState({
    dateFrom: "",
    dateTo: "",
    workflowCode: "",
  });
  const [positions, setPositions] = useState<InventoryPosition[]>([]);
  const [inventoryFilters, setInventoryFilters] = useState({
    storeNumber: "",
    productCode: "",
  });
  const [schedules, setSchedules] = useState<ReportSchedule[]>([]);
  const [runs, setRuns] = useState<ReportRun[]>([]);
  const [scheduleName, setScheduleName] = useState("Daily inventory position");
  const [scheduleType, setScheduleType] = useState("inventory_position");
  const [message, setMessage] = useState<string | null>(null);
  const canManageReports =
    user?.permissions.includes("analytics.reports.manage") ?? false;
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (mode !== "executive") return;
    void getOperationalDashboard()
      .then(setDashboard)
      .catch((reason: unknown) =>
        setError(
          reason instanceof Error ? reason.message : "Unable to load analytics",
        ),
      );
  }, [mode]);

  useEffect(() => {
    if (mode !== "reports") return;
    void getInventoryPositions(inventoryFilters)
      .then((inventory) => setPositions(inventory.positions))
      .catch((reason: unknown) =>
        setError(
          reason instanceof Error ? reason.message : "Unable to load reports",
        ),
      );
  }, [inventoryFilters, mode]);

  useEffect(() => {
    if (mode !== "reports") return;
    void Promise.all([listReportSchedules(), listReportRuns()])
      .then(([nextSchedules, nextRuns]) => {
        setSchedules(nextSchedules);
        setRuns(nextRuns);
      })
      .catch((reason: unknown) =>
        setError(
          reason instanceof Error ? reason.message : "Unable to load reports",
        ),
      );
  }, [mode]);

  function updateInventoryFilter(
    field: "storeNumber" | "productCode",
    value: string,
  ) {
    setInventoryFilters((current) => ({ ...current, [field]: value }));
  }

  useEffect(() => {
    if (mode !== "executive") return;
    void getWorkflowAnalytics(workflowFilters)
      .then((result) => setWorkflowMetrics(result.workflows))
      .catch((reason: unknown) =>
        setError(
          reason instanceof Error
            ? reason.message
            : "Unable to load workflow analytics",
        ),
      );
  }, [workflowFilters, mode]);

  function updateWorkflowFilter(
    field: "dateFrom" | "dateTo" | "workflowCode",
    value: string,
  ) {
    setWorkflowFilters((current) => ({ ...current, [field]: value }));
  }

  useEffect(() => {
    if (mode !== "executive") return;
    void getSpendAnalysis(spendDimension, spendFilters)
      .then(setSpend)
      .catch((reason: unknown) =>
        setError(
          reason instanceof Error
            ? reason.message
            : "Unable to load spend analysis",
        ),
      );
  }, [mode, spendDimension, spendFilters]);

  function updateSpendFilter(field: keyof SpendFilters, value: string) {
    setSpendFilterDraft((current) => ({
      ...current,
      [field]: value || undefined,
    }));
  }

  function applySpendFilters() {
    setSpendFilters({ ...spendFilterDraft });
  }

  function clearSpendFilters() {
    setSpendFilterDraft({});
    setSpendFilters({});
  }

  useEffect(() => {
    if (mode !== "vendor") return;
    void getVendorScorecards(scorecardFilters)
      .then((result) => setScorecards(result.scorecards))
      .catch((reason: unknown) =>
        setError(
          reason instanceof Error
            ? reason.message
            : "Unable to load vendor scorecards",
        ),
      );
  }, [mode, scorecardFilters]);

  function updateScorecardFilter(
    field: "dateFrom" | "dateTo" | "minimumOrders",
    value: string,
  ) {
    setScorecardFilters((current) => ({
      ...current,
      [field]:
        field === "minimumOrders" ? Math.max(1, Number(value) || 1) : value,
    }));
  }

  if (error)
    return (
      <main className="p-8">
        <p className="rounded bg-red-50 p-4 text-red-800">{error}</p>
      </main>
    );
  if (mode === "executive" && !dashboard)
    return <main className="p-8">Loading analytics…</main>;

  const headline = dashboard
    ? ([
        ["Purchase orders", dashboard.purchasing.purchase_order_count],
        ["Receipts", dashboard.receiving.receipt_count],
        ["Open variances", dashboard.receiving.open_variance_count],
        ["Open backorders", dashboard.receiving.open_backorder_count],
        ["Invoices", dashboard.invoices.invoice_count],
        [
          "Open match exceptions",
          dashboard.reconciliation.open_exception_count,
        ],
      ] as const)
    : [];

  async function download(blobPromise: Promise<Blob>, filename: string) {
    try {
      const blob = await blobPromise;
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = filename;
      anchor.click();
      URL.revokeObjectURL(url);
    } catch (reason) {
      setMessage(reason instanceof Error ? reason.message : "Download failed");
    }
  }

  async function createSchedule(event: FormEvent) {
    event.preventDefault();
    try {
      await createReportSchedule({
        name: scheduleName,
        report_type: scheduleType,
        parameters: {},
        interval_minutes: 1440,
      });
      const nextSchedules = await listReportSchedules();
      setSchedules(nextSchedules);
      setMessage("Report schedule created.");
    } catch (reason) {
      setMessage(
        reason instanceof Error ? reason.message : "Schedule creation failed",
      );
    }
  }

  async function generateDue() {
    try {
      const generated = await runDueReports();
      setRuns(await listReportRuns());
      setSchedules(await listReportSchedules());
      setMessage(`${generated.length} due report(s) generated.`);
    } catch (reason) {
      setMessage(
        reason instanceof Error ? reason.message : "Report generation failed",
      );
    }
  }

  return (
    <main className="mx-auto max-w-7xl p-8">
      <header className="mb-8">
        <Link className="text-sm text-blue-700" href="/">
          ← Dashboard
        </Link>
        <h1 className="mt-2 text-3xl font-bold">
          {mode === "vendor"
            ? "Vendor Performance"
            : mode === "reports"
              ? "Reports"
              : "Executive Analytics"}
        </h1>
        <p className="mt-1 text-slate-600">
          {mode === "vendor"
            ? "Compare vendor spend, delivery, acknowledgement, and exception performance."
            : mode === "reports"
              ? "Generate and download general platform reports and exports."
              : "Purchasing, receiving, invoice, and reconciliation health."}
        </p>
      </header>
      {message ? (
        <p className="mb-6 rounded bg-slate-100 p-3 text-sm">{message}</p>
      ) : null}
      {mode === "executive" ? (
        <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {headline.map(([label, value]) => (
            <div className="rounded-lg bg-white p-5 shadow" key={label}>
              <p className="text-sm text-slate-500">{label}</p>
              <p className="mt-1 text-3xl font-semibold">{value}</p>
            </div>
          ))}
        </section>
      ) : null}
      {mode === "executive" ? (
        <section className="mt-6 grid gap-6 lg:grid-cols-2">
          <article className="rounded-lg bg-white p-6 shadow">
            <h2 className="text-xl font-semibold">Purchase orders</h2>
            <StatusList items={dashboard!.purchasing.purchase_order_statuses} />
            <h3 className="mt-5 font-medium">Ordered spend</h3>
            <div className="mt-2 space-y-2">
              {dashboard!.purchasing.ordered_spend.map((item) => (
                <div className="flex justify-between" key={item.currency}>
                  <span>{item.currency}</span>
                  <span className="font-semibold">{item.amount}</span>
                </div>
              ))}
            </div>
          </article>
          <article className="rounded-lg bg-white p-6 shadow">
            <h2 className="text-xl font-semibold">Receiving quality</h2>
            <dl className="mt-4 grid grid-cols-2 gap-4">
              <div>
                <dt className="text-sm text-slate-500">Accepted units</dt>
                <dd className="text-2xl font-semibold">
                  {dashboard!.receiving.accepted_quantity}
                </dd>
              </div>
              <div>
                <dt className="text-sm text-slate-500">Rejected units</dt>
                <dd className="text-2xl font-semibold">
                  {dashboard!.receiving.rejected_quantity}
                </dd>
              </div>
              <div>
                <dt className="text-sm text-slate-500">Outstanding BO units</dt>
                <dd className="text-2xl font-semibold">
                  {dashboard!.receiving.outstanding_backorder_quantity}
                </dd>
              </div>
            </dl>
          </article>
          <article className="rounded-lg bg-white p-6 shadow">
            <h2 className="text-xl font-semibold">Invoices</h2>
            <StatusList items={dashboard!.invoices.invoice_statuses} />
            <h3 className="mt-5 font-medium">Invoiced amount</h3>
            <div className="mt-2 space-y-2">
              {dashboard!.invoices.invoiced_amount.map((item) => (
                <div className="flex justify-between" key={item.currency}>
                  <span>{item.currency}</span>
                  <span className="font-semibold">{item.amount}</span>
                </div>
              ))}
            </div>
            <p className="mt-4 text-sm text-amber-700">
              {dashboard!.invoices.line_match_exception_count} line match
              exception(s)
            </p>
          </article>
          <article className="rounded-lg bg-white p-6 shadow">
            <h2 className="text-xl font-semibold">Reconciliation</h2>
            <StatusList items={dashboard!.reconciliation.case_statuses} />
          </article>
        </section>
      ) : null}
      {mode === "executive" ? (
        <section className="mt-6 rounded-lg bg-white p-6 shadow">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div>
              <h2 className="text-xl font-semibold">
                Spend and product performance
              </h2>
              <p className="text-sm text-slate-500">
                Highest-volume vendors, departments, and product codes are
                listed first. Landed line spend remains separated by currency.
              </p>
            </div>
            <button
              className="text-sm font-semibold text-blue-700"
              onClick={() =>
                void download(
                  downloadAnalyticsExport("spend", {
                    group_by: spendDimension,
                    date_from: spendFilters.dateFrom,
                    date_to: spendFilters.dateTo,
                    vendor_code: spendFilters.vendorCode,
                    store_number: spendFilters.storeNumber,
                    workflow_code: spendFilters.workflowCode,
                  }),
                  "spend-analysis.xlsx",
                )
              }
              type="button"
            >
              Export filtered Excel
            </button>
            <label className="text-sm font-medium">
              Group by
              <select
                className="ml-2 rounded border p-2"
                onChange={(event) =>
                  setSpendDimension(event.target.value as SpendDimension)
                }
                value={spendDimension}
              >
                <option value="vendor">Vendor</option>
                <option value="department">Department</option>
                <option value="product_code">Product Code</option>
              </select>
            </label>
          </div>
          <div className="mt-4 grid gap-3 rounded border bg-slate-50 p-3 sm:grid-cols-2 lg:grid-cols-5">
            <label className="text-xs font-semibold text-slate-600">
              From
              <input
                className="mt-1 w-full rounded border bg-white p-2 text-sm font-normal"
                onChange={(event) =>
                  updateSpendFilter("dateFrom", event.target.value)
                }
                type="date"
                value={spendFilterDraft.dateFrom ?? ""}
              />
            </label>
            <label className="text-xs font-semibold text-slate-600">
              To
              <input
                className="mt-1 w-full rounded border bg-white p-2 text-sm font-normal"
                onChange={(event) =>
                  updateSpendFilter("dateTo", event.target.value)
                }
                type="date"
                value={spendFilterDraft.dateTo ?? ""}
              />
            </label>
            <label className="text-xs font-semibold text-slate-600">
              Vendor code
              <input
                className="mt-1 w-full rounded border bg-white p-2 text-sm font-normal"
                onChange={(event) =>
                  updateSpendFilter("vendorCode", event.target.value.trim())
                }
                placeholder="Any vendor"
                value={spendFilterDraft.vendorCode ?? ""}
              />
            </label>
            <label className="text-xs font-semibold text-slate-600">
              Store number
              <input
                className="mt-1 w-full rounded border bg-white p-2 text-sm font-normal"
                onChange={(event) =>
                  updateSpendFilter("storeNumber", event.target.value.trim())
                }
                placeholder="Any store"
                value={spendFilterDraft.storeNumber ?? ""}
              />
            </label>
            <label className="text-xs font-semibold text-slate-600">
              Workflow
              <input
                className="mt-1 w-full rounded border bg-white p-2 text-sm font-normal"
                onChange={(event) =>
                  updateSpendFilter("workflowCode", event.target.value.trim())
                }
                placeholder="Any workflow"
                value={spendFilterDraft.workflowCode ?? ""}
              />
            </label>
            <div className="flex items-end gap-2 sm:col-span-2 lg:col-span-5">
              <button
                className="rounded bg-slate-900 px-4 py-2 text-sm font-semibold text-white"
                onClick={applySpendFilters}
                type="button"
              >
                Apply filters
              </button>
              <button
                className="rounded border px-4 py-2 text-sm font-semibold"
                onClick={clearSpendFilters}
                type="button"
              >
                Clear
              </button>
            </div>
          </div>
          <div className="mt-4 overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b">
                  <th className="p-2 capitalize">{spendDimension}</th>
                  <th className="p-2">Currency</th>
                  <th className="p-2">Orders</th>
                  <th className="p-2">Lines</th>
                  <th className="p-2">Quantity</th>
                  <th className="p-2">Amount</th>
                </tr>
              </thead>
              <tbody>
                {spend?.metrics.map((item) => (
                  <tr
                    className="border-b"
                    key={`${item.dimension_key}-${item.currency}`}
                  >
                    <td className="p-2 font-medium">{item.dimension_key}</td>
                    <td className="p-2">{item.currency}</td>
                    <td className="p-2">{item.purchase_order_count}</td>
                    <td className="p-2">{item.line_count}</td>
                    <td className="p-2">{item.quantity}</td>
                    <td className="p-2 font-semibold">{item.amount}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            {spend?.metrics.length === 0 ? (
              <p className="p-4 text-sm text-slate-500">
                No spend matches this view.
              </p>
            ) : null}
          </div>
        </section>
      ) : null}
      {mode === "vendor" ? (
        <section className="mt-6 rounded-lg bg-white p-6 shadow">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <h2 className="text-xl font-semibold">Vendor scorecards</h2>
              <p className="text-sm text-slate-500">
                Transparent component rates; Not measured means the denominator
                is zero.
              </p>
            </div>
            <button
              className="text-sm font-semibold text-blue-700"
              onClick={() =>
                void download(
                  downloadAnalyticsExport("vendor_scorecards", {
                    date_from: scorecardFilters.dateFrom,
                    date_to: scorecardFilters.dateTo,
                    minimum_orders: scorecardFilters.minimumOrders,
                  }),
                  "vendor-scorecards.xlsx",
                )
              }
              type="button"
            >
              Export filtered Excel
            </button>
            <div className="grid gap-2 text-xs font-semibold text-slate-600 sm:grid-cols-3">
              <label>
                From
                <input
                  className="mt-1 block rounded border p-2 text-sm font-normal"
                  onChange={(event) =>
                    updateScorecardFilter("dateFrom", event.target.value)
                  }
                  type="date"
                  value={scorecardFilters.dateFrom}
                />
              </label>
              <label>
                To
                <input
                  className="mt-1 block rounded border p-2 text-sm font-normal"
                  onChange={(event) =>
                    updateScorecardFilter("dateTo", event.target.value)
                  }
                  type="date"
                  value={scorecardFilters.dateTo}
                />
              </label>
              <label>
                Minimum orders
                <input
                  className="mt-1 block w-full rounded border p-2 text-sm font-normal"
                  min={1}
                  onChange={(event) =>
                    updateScorecardFilter("minimumOrders", event.target.value)
                  }
                  type="number"
                  value={scorecardFilters.minimumOrders}
                />
              </label>
            </div>
          </div>
          <div className="mt-4 overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b">
                  <th className="p-2">Vendor</th>
                  <th className="p-2">Orders</th>
                  <th className="p-2">Ordered spend</th>
                  <th className="p-2">Ack coverage</th>
                  <th className="p-2">On-time delivery</th>
                  <th className="p-2">Receiving acceptance</th>
                  <th className="p-2">Invoice match</th>
                  <th className="p-2">Delays</th>
                  <th className="p-2">Backorders</th>
                  <th className="p-2">Out of stock</th>
                  <th className="p-2">Substitutions</th>
                  <th className="p-2">Confirmed changes</th>
                  <th className="p-2">Approved / rejected</th>
                </tr>
              </thead>
              <tbody>
                {scorecards.map((item) => (
                  <tr className="border-b" key={item.vendor_code}>
                    <td className="p-2">
                      <span className="font-medium">{item.vendor_name}</span>
                      <br />
                      <span className="text-xs text-slate-500">
                        {item.vendor_code}
                      </span>
                    </td>
                    <td className="p-2">{item.purchase_order_count}</td>
                    <td className="p-2">
                      {item.ordered_spend.length
                        ? item.ordered_spend
                            .map((spend) => `${spend.currency} ${spend.amount}`)
                            .join(" · ")
                        : "—"}
                    </td>
                    <td className="p-2">
                      {item.acknowledgement_coverage_rate === null
                        ? "Not measured"
                        : `${item.acknowledgement_coverage_rate}%`}
                    </td>
                    <td className="p-2">
                      {item.on_time_delivery_rate === null
                        ? "Not measured"
                        : `${item.on_time_delivery_rate}%`}
                    </td>
                    <td className="p-2">
                      {item.receiving_acceptance_rate === null
                        ? "Not measured"
                        : `${item.receiving_acceptance_rate}%`}
                    </td>
                    <td className="p-2">
                      {item.invoice_match_rate === null
                        ? "Not measured"
                        : `${item.invoice_match_rate}%`}
                    </td>
                    <td className="p-2">{item.delay_event_count}</td>
                    <td className="p-2">{item.backorder_event_count}</td>
                    <td className="p-2">{item.out_of_stock_event_count}</td>
                    <td className="p-2">{item.substitution_event_count}</td>
                    <td className="p-2">{item.confirmed_po_change_count}</td>
                    <td className="p-2">
                      {item.approved_reconciliation_count} /{" "}
                      {item.rejected_reconciliation_count}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {scorecards.length === 0 ? (
              <p className="p-4 text-sm text-slate-500">
                No vendors meet the current scorecard threshold.
              </p>
            ) : null}
          </div>
        </section>
      ) : null}
      {mode === "executive" ? (
        <section className="mt-6 rounded-lg bg-white p-6 shadow">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <h2 className="text-xl font-semibold">
                Approval and workflow performance
              </h2>
              <p className="text-sm text-slate-500">
                Completion timing includes terminal workflow instances only.
              </p>
            </div>
            <button
              className="text-sm font-semibold text-blue-700"
              onClick={() =>
                void download(
                  downloadAnalyticsExport("workflows", {
                    date_from: workflowFilters.dateFrom,
                    date_to: workflowFilters.dateTo,
                    workflow_code: workflowFilters.workflowCode,
                  }),
                  "workflow-analytics.xlsx",
                )
              }
              type="button"
            >
              Export filtered Excel
            </button>
            <div className="grid gap-2 text-xs font-semibold text-slate-600 sm:grid-cols-3">
              <label>
                From
                <input
                  className="mt-1 block rounded border p-2 text-sm font-normal"
                  onChange={(event) =>
                    updateWorkflowFilter("dateFrom", event.target.value)
                  }
                  type="date"
                  value={workflowFilters.dateFrom}
                />
              </label>
              <label>
                To
                <input
                  className="mt-1 block rounded border p-2 text-sm font-normal"
                  onChange={(event) =>
                    updateWorkflowFilter("dateTo", event.target.value)
                  }
                  type="date"
                  value={workflowFilters.dateTo}
                />
              </label>
              <label>
                Workflow code
                <input
                  className="mt-1 block rounded border p-2 text-sm font-normal"
                  onChange={(event) =>
                    updateWorkflowFilter(
                      "workflowCode",
                      event.target.value.trim(),
                    )
                  }
                  placeholder="Any workflow"
                  value={workflowFilters.workflowCode}
                />
              </label>
            </div>
          </div>
          <div className="mt-4 grid gap-4 lg:grid-cols-2">
            {workflowMetrics.map((item) => (
              <article className="rounded border p-4" key={item.workflow_code}>
                <h3 className="font-semibold">{item.workflow_code}</h3>
                <dl className="mt-3 grid grid-cols-3 gap-3 text-sm">
                  <div>
                    <dt className="text-slate-500">Active</dt>
                    <dd className="text-xl font-semibold">
                      {item.active_count}
                    </dd>
                  </div>
                  <div>
                    <dt className="text-slate-500">Completed</dt>
                    <dd className="text-xl font-semibold">
                      {item.completed_count}
                    </dd>
                  </div>
                  <div>
                    <dt className="text-slate-500">Transitions</dt>
                    <dd className="text-xl font-semibold">
                      {item.transition_count}
                    </dd>
                  </div>
                </dl>
                <p className="mt-3 text-sm">
                  Approvals / rejections:{" "}
                  <strong>
                    {item.approval_count} / {item.rejection_count}
                  </strong>
                </p>
                <div className="mt-3 grid grid-cols-3 gap-2 text-xs">
                  <div>
                    <span className="text-slate-500">Average</span>
                    <br />
                    {item.average_completion_seconds ?? "Not measured"}s
                  </div>
                  <div>
                    <span className="text-slate-500">Median</span>
                    <br />
                    {item.median_completion_seconds ?? "Not measured"}s
                  </div>
                  <div>
                    <span className="text-slate-500">P90</span>
                    <br />
                    {item.p90_completion_seconds ?? "Not measured"}s
                  </div>
                </div>
                {item.approval_actors.length ? (
                  <div className="mt-4 border-t pt-3 text-xs">
                    {item.approval_actors.map((actor) => (
                      <div
                        className="flex justify-between gap-3"
                        key={actor.actor}
                      >
                        <span className="truncate">{actor.actor}</span>
                        <span>
                          {actor.approval_count} / {actor.rejection_count}
                        </span>
                      </div>
                    ))}
                  </div>
                ) : null}
              </article>
            ))}
          </div>
          {workflowMetrics.length === 0 ? (
            <p className="mt-4 text-sm text-slate-500">
              No workflow instances are available.
            </p>
          ) : null}
        </section>
      ) : null}
      {mode === "reports" ? (
        <section className="mt-6 rounded-lg bg-white p-6 shadow">
          <div>
            <h2 className="text-xl font-semibold">Export center</h2>
            <p className="text-sm text-slate-500">
              Download current operational reports without duplicating their
              interactive workspaces here.
            </p>
          </div>
          <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {reportExports.map((report) => (
              <article
                className="flex min-h-40 flex-col rounded-lg border p-4"
                key={report.filename}
              >
                <h3 className="font-semibold">{report.label}</h3>
                <p className="mt-2 flex-1 text-sm text-slate-500">
                  {report.description}
                </p>
                <button
                  className="mt-4 w-fit text-sm font-semibold text-blue-700"
                  onClick={() =>
                    void download(
                      downloadAnalyticsExport(
                        report.reportType,
                        report.parameters,
                      ),
                      report.filename,
                    )
                  }
                  type="button"
                >
                  Download Excel
                </button>
              </article>
            ))}
          </div>
        </section>
      ) : null}
      {mode === "reports" ? (
        <section className="mt-6 rounded-lg bg-white p-6 shadow">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div>
              <h2 className="text-xl font-semibold">
                Receiving inventory position
              </h2>
              <p className="text-sm text-slate-500">
                Cumulative accepted receipts—not calculated on-hand inventory.
              </p>
            </div>
            <button
              className="text-blue-700"
              onClick={() =>
                void download(
                  downloadAnalyticsExport("inventory_position", {
                    store_number: inventoryFilters.storeNumber,
                    product_code: inventoryFilters.productCode,
                  }),
                  "inventory-position.xlsx",
                )
              }
              type="button"
            >
              Export Excel
            </button>
          </div>
          <div className="mt-4 grid gap-3 rounded border bg-slate-50 p-3 sm:grid-cols-2">
            <label className="text-xs font-semibold text-slate-600">
              Store number
              <input
                className="mt-1 block w-full rounded border bg-white p-2 text-sm font-normal"
                onChange={(event) =>
                  updateInventoryFilter(
                    "storeNumber",
                    event.target.value.trim(),
                  )
                }
                placeholder="All stores"
                value={inventoryFilters.storeNumber}
              />
            </label>
            <label className="text-xs font-semibold text-slate-600">
              Product code
              <input
                className="mt-1 block w-full rounded border bg-white p-2 text-sm font-normal"
                onChange={(event) =>
                  updateInventoryFilter(
                    "productCode",
                    event.target.value.trim(),
                  )
                }
                placeholder="All products"
                value={inventoryFilters.productCode}
              />
            </label>
          </div>
          <div className="mt-4 overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b">
                  <th className="p-2">Store</th>
                  <th className="p-2">Product</th>
                  <th className="p-2">Accepted</th>
                  <th className="p-2">Rejected</th>
                  <th className="p-2">Outstanding BO</th>
                </tr>
              </thead>
              <tbody>
                {positions.map((item) => (
                  <tr
                    className="border-b"
                    key={`${item.store_number}-${item.product_code}`}
                  >
                    <td className="p-2">{item.store_number}</td>
                    <td className="p-2">
                      <span className="font-medium">{item.product_code}</span>
                      <br />
                      <span className="text-xs text-slate-500">
                        {item.product_name}
                      </span>
                    </td>
                    <td className="p-2">{item.accepted_quantity}</td>
                    <td className="p-2">{item.rejected_quantity}</td>
                    <td className="p-2">
                      {item.outstanding_backorder_quantity}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {positions.length === 0 ? (
              <p className="p-4 text-sm text-slate-500">
                No accepted receipts are available.
              </p>
            ) : null}
          </div>
        </section>
      ) : null}
      {mode === "reports" ? (
        <section className="mt-6 grid gap-6 lg:grid-cols-2">
          <article className="rounded-lg bg-white p-6 shadow">
            <div className="flex items-center justify-between gap-3">
              <h2 className="text-xl font-semibold">Scheduled reports</h2>
              {canManageReports ? (
                <button
                  className="text-blue-700"
                  onClick={() => void generateDue()}
                  type="button"
                >
                  Generate due
                </button>
              ) : null}
            </div>
            {canManageReports ? (
              <form className="mt-4 grid gap-3" onSubmit={createSchedule}>
                <input
                  className="rounded border p-2"
                  onChange={(event) => setScheduleName(event.target.value)}
                  required
                  value={scheduleName}
                />
                <select
                  className="rounded border p-2"
                  onChange={(event) => setScheduleType(event.target.value)}
                  value={scheduleType}
                >
                  <option value="inventory_position">Inventory position</option>
                  <option value="executive_pack">Executive report pack</option>
                  <option value="spend">Spend</option>
                  <option value="vendor_scorecards">Vendor scorecards</option>
                  <option value="workflows">Workflows</option>
                </select>
                <button
                  className="rounded bg-slate-900 px-4 py-2 text-white"
                  type="submit"
                >
                  Create daily schedule
                </button>
              </form>
            ) : null}
            <div className="mt-4 space-y-2">
              {schedules.map((item) => (
                <div className="rounded border p-3 text-sm" key={item.id}>
                  <p className="font-medium">{item.name}</p>
                  <p className="text-slate-500">
                    {item.report_type.replaceAll("_", " ")} · next{" "}
                    {new Date(item.next_run_at).toLocaleString()}
                  </p>
                </div>
              ))}
            </div>
          </article>
          <article className="rounded-lg bg-white p-6 shadow">
            <h2 className="text-xl font-semibold">Report runs</h2>
            <div className="mt-4 space-y-2">
              {runs.map((item) => (
                <div
                  className="flex items-center justify-between gap-3 rounded border p-3 text-sm"
                  key={item.id}
                >
                  <div>
                    <p className="font-medium">{item.status}</p>
                    <p className="text-xs text-slate-500">
                      {new Date(item.created_at).toLocaleString()} ·{" "}
                      {item.size_bytes ?? 0} bytes
                    </p>
                  </div>
                  {item.status === "completed" ? (
                    <button
                      className="text-blue-700"
                      onClick={() =>
                        void download(
                          downloadReportRun(item.id),
                          `analytics-${item.id}.${
                            item.content_type?.includes("spreadsheetml")
                              ? "xlsx"
                              : "csv"
                          }`,
                        )
                      }
                      type="button"
                    >
                      Download
                    </button>
                  ) : null}
                </div>
              ))}
            </div>
          </article>
        </section>
      ) : null}
    </main>
  );
}
