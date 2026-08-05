"use client";

import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import { ManagedEvent } from "@/lib/event-admin-api";
import {
  downloadArchivedEventOrderBackup,
  EventOrderBackupArtifact,
  exportEventOrderBackup,
  getArchivedEventOrderBackup,
} from "@/lib/event-order-review-api";
import {
  configureEventSettlement,
  createEventSettlementException,
  EventSettlementExportReport,
  EventSettlementStatus,
  EventSettlementSummary,
  exportEventSettlementReport,
  getEventSettlementSummary,
  reopenEventSettlementException,
  resolveEventSettlementException,
} from "@/lib/event-settlement-api";

const settlementStatuses: Array<{
  value: EventSettlementStatus;
  label: string;
}> = [
  { value: "draft", label: "Draft" },
  { value: "collecting_evidence", label: "Collecting evidence" },
  { value: "exceptions_present", label: "Exceptions present" },
  { value: "ready_for_review", label: "Ready for review" },
  { value: "approved", label: "Approved" },
  { value: "closed", label: "Closed" },
];

const exportReports: Array<{
  type: EventSettlementExportReport;
  label: string;
}> = [
  { type: "closeout-packet", label: "Full closeout packet" },
  { type: "reconciliation-detail", label: "Reconciliation detail" },
  { type: "summary", label: "Settlement summary" },
  { type: "exceptions", label: "Exception list" },
  { type: "order-closeout", label: "Order closeout" },
  { type: "loadout-closeout", label: "Loadout closeout" },
  { type: "feedback", label: "Feedback report" },
  { type: "audit-log", label: "Audit log" },
];

function statusLabel(value: string) {
  return value.replaceAll("_", " ");
}

function displayDateTime(value: string | null) {
  if (!value) return "Not started";
  return new Date(value).toLocaleString([], {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

function formatCurrency(value: string) {
  return Number(value || "0").toLocaleString([], {
    style: "currency",
    currency: "USD",
  });
}

function numericValue(value: number | string | null | undefined) {
  return Number(value ?? 0);
}

const reconciliationExceptionTypes = new Set([
  "ordered_not_loaded",
  "loaded_not_ordered",
  "quantity_mismatch",
]);

export function EventSettlementAdministrationPanel({
  event,
  readOnly = false,
  onCompleted,
}: {
  event: ManagedEvent;
  readOnly?: boolean;
  onCompleted?: () => void | Promise<void>;
}) {
  const [summary, setSummary] = useState<EventSettlementSummary | null>(null);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [archivedBackup, setArchivedBackup] =
    useState<EventOrderBackupArtifact | null>(null);

  const load = useCallback(async () => {
    const nextSummary = await getEventSettlementSummary(event.id);
    setSummary(nextSummary);
    setArchivedBackup(
      nextSummary.status === "closed"
        ? await getArchivedEventOrderBackup(event.id).catch(() => null)
        : null,
    );
  }, [event.id]);

  useEffect(() => {
    setMessage(null);
    setError(null);
    let active = true;
    const refresh = () =>
      void load().catch((caught: unknown) => {
        if (active) {
          setError(
            caught instanceof Error
              ? caught.message
              : "Unable to load event settlement.",
          );
        }
      });
    refresh();
    const timer = window.setInterval(refresh, 30_000);
    return () => {
      active = false;
      window.clearInterval(timer);
    };
  }, [load]);

  const readinessTone = useMemo(() => {
    const readiness = numericValue(summary?.readiness_percentage);
    if (readiness >= 100) return "text-green-800";
    if (readiness >= 70) return "text-blue-800";
    return "text-amber-800";
  }, [summary?.readiness_percentage]);

  const reconciliationExceptions = useMemo(
    () =>
      (summary?.exceptions ?? []).filter(
        (exception) =>
          exception.status === "open" &&
          reconciliationExceptionTypes.has(exception.exception_type),
      ),
    [summary?.exceptions],
  );

  async function saveSettlement(formEvent: FormEvent<HTMLFormElement>) {
    formEvent.preventDefault();
    const data = new FormData(formEvent.currentTarget);
    setBusy(true);
    setMessage(null);
    setError(null);
    try {
      const nextSummary = await configureEventSettlement(event.id, {
        status: String(data.get("status")) as EventSettlementStatus,
        notes: String(data.get("notes") || "") || null,
      });
      setSummary(nextSummary);
      if (nextSummary.status === "closed") await onCompleted?.();
      setMessage("Event settlement settings saved.");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Settlement failed.");
    } finally {
      setBusy(false);
    }
  }

  async function downloadReport(reportType: EventSettlementExportReport) {
    setBusy(true);
    setMessage(null);
    setError(null);
    try {
      await exportEventSettlementReport(event.id, reportType);
      setMessage("Event settlement export downloaded.");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Export failed.");
    } finally {
      setBusy(false);
    }
  }

  async function downloadOrderBackup() {
    setBusy(true);
    setMessage(null);
    setError(null);
    try {
      await exportEventOrderBackup(event.id, event.name);
      setMessage("Complete event order backup downloaded.");
    } catch (caught) {
      setError(
        caught instanceof Error
          ? caught.message
          : "Order backup export failed.",
      );
    } finally {
      setBusy(false);
    }
  }

  async function downloadArchivedBackup() {
    setBusy(true);
    setMessage(null);
    setError(null);
    try {
      await downloadArchivedEventOrderBackup(event.id, event.name);
      setMessage("Archived closeout order backup downloaded.");
    } catch (caught) {
      setError(
        caught instanceof Error
          ? caught.message
          : "Archived backup download failed.",
      );
    } finally {
      setBusy(false);
    }
  }

  async function createException(formEvent: FormEvent<HTMLFormElement>) {
    formEvent.preventDefault();
    const data = new FormData(formEvent.currentTarget);
    setBusy(true);
    setMessage(null);
    setError(null);
    try {
      const nextSummary = await createEventSettlementException(event.id, {
        exception_type: String(data.get("exception_type") || ""),
        severity: String(data.get("severity") || "medium"),
        reference_type: String(data.get("reference_type") || "") || null,
        reference_id: String(data.get("reference_id") || "") || null,
        description: String(data.get("description") || ""),
      });
      setSummary(nextSummary);
      formEvent.currentTarget.reset();
      setMessage("Settlement exception added.");
    } catch (caught) {
      setError(
        caught instanceof Error
          ? caught.message
          : "Unable to add the exception.",
      );
    } finally {
      setBusy(false);
    }
  }

  async function resolveException(exceptionId: string) {
    setBusy(true);
    setMessage(null);
    setError(null);
    try {
      const nextSummary = await resolveEventSettlementException(exceptionId, {
        resolution_notes: "Resolved from settlement administration.",
      });
      setSummary(nextSummary);
      setMessage("Settlement exception resolved.");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Resolve failed.");
    } finally {
      setBusy(false);
    }
  }

  async function reopenException(exceptionId: string) {
    setBusy(true);
    setMessage(null);
    setError(null);
    try {
      const nextSummary = await reopenEventSettlementException(exceptionId);
      setSummary(nextSummary);
      setMessage("Settlement exception reopened.");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Reopen failed.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="event-ui rounded-2xl border bg-white p-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="brand-eyebrow">023 · Event Settlement</p>
          <h3 className="text-xl font-bold">Closeout reconciliation</h3>
          <p className="mt-1 text-sm text-slate-600">
            Compare released orders, signed loadouts, venue releases, and open
            exceptions before final settlement.
          </p>
        </div>
        <div className="rounded-xl border bg-slate-50 p-3 text-right">
          <span className="block text-xs font-bold uppercase text-slate-500">
            Current status
          </span>
          <strong className="capitalize">
            {statusLabel(summary?.status ?? "draft")}
          </strong>
        </div>
      </div>

      {message ? (
        <p className="mt-3 rounded-lg bg-green-50 p-3 text-green-800">
          {message}
        </p>
      ) : null}
      {error ? (
        <p className="mt-3 rounded-lg bg-red-50 p-3 text-red-800">{error}</p>
      ) : null}
      {summary?.vendor_hall_closeout_ready === false ? (
        <p className="mt-3 rounded-lg border border-amber-300 bg-amber-50 p-3 text-sm text-amber-950">
          <strong className="block">
            Vendor Hall closeout is still pending
          </strong>
          Close all vendor booths before approving or closing settlement.
          Current Vendor Hall status:{" "}
          {statusLabel(summary.vendor_hall_status ?? "unknown")}.
        </p>
      ) : null}

      <div className="mt-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-6">
        <Metric label="Orders" value={summary?.order_total ?? 0} />
        <Metric label="Released" value={summary?.order_released ?? 0} />
        <Metric label="Units" value={summary?.approved_units ?? 0} />
        <Metric
          label="Approved spend"
          value={formatCurrency(summary?.approved_spend ?? "0")}
        />
        <Metric
          label="Loadouts"
          value={summary?.loadout_assignment_total ?? 0}
        />
        <Metric
          label="Awaiting review"
          value={summary?.loadout_final_review_pending ?? 0}
        />
        <Metric
          label="Open exceptions"
          value={summary?.open_exception_count ?? 0}
        />
      </div>

      <section className="mt-5 rounded-2xl border bg-slate-50 p-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <p className="brand-eyebrow">Settlement readiness</p>
            <h4 className="font-bold">Closeout progress</h4>
          </div>
          <strong className={`text-3xl ${readinessTone}`}>
            {numericValue(summary?.readiness_percentage)}%
          </strong>
        </div>
        <div className="mt-4 h-3 overflow-hidden rounded-full bg-white">
          <div
            className="h-full rounded-full bg-blue-800 transition-all"
            style={{
              width: `${Math.min(numericValue(summary?.readiness_percentage), 100)}%`,
            }}
          />
        </div>
        <div className="mt-4 grid gap-3 text-sm md:grid-cols-3">
          <div className="rounded-xl bg-white p-3">
            <span className="block text-xs font-bold uppercase text-slate-500">
              Signed packing lists
            </span>
            {summary?.loadout_signed ?? 0} /{" "}
            {summary?.loadout_assignment_total ?? 0}
          </div>
          <div className="rounded-xl bg-white p-3">
            <span className="block text-xs font-bold uppercase text-slate-500">
              Stores released
            </span>
            {summary?.loadout_released ?? 0} /{" "}
            {summary?.loadout_assignment_total ?? 0}
          </div>
          <div className="rounded-xl bg-white p-3">
            <span className="block text-xs font-bold uppercase text-slate-500">
              Final review queue
            </span>
            {summary?.loadout_final_review_pending ?? 0} waiting on event staff
          </div>
          <div className="rounded-xl bg-white p-3">
            <span className="block text-xs font-bold uppercase text-slate-500">
              Last updated
            </span>
            {displayDateTime(summary?.updated_at ?? null)}
          </div>
        </div>
      </section>

      <section className="mt-5 rounded-2xl border bg-white p-4">
        <p className="brand-eyebrow">Order / loadout reconciliation</p>
        <h4 className="font-bold">Generated matching checks</h4>
        <p className="mt-1 text-sm text-slate-600">
          Compare released event orders against venue-released loadouts by
          entity, vendor, and model number.
        </p>
        <div className="mt-4 grid gap-3 text-sm md:grid-cols-3">
          <div className="rounded-xl bg-slate-50 p-3">
            <span className="block text-xs font-bold uppercase text-slate-500">
              Ordered not loaded
            </span>
            <strong className="text-2xl">
              {summary?.ordered_not_loaded_count ?? 0}
            </strong>
          </div>
          <div className="rounded-xl bg-slate-50 p-3">
            <span className="block text-xs font-bold uppercase text-slate-500">
              Loaded not ordered
            </span>
            <strong className="text-2xl">
              {summary?.loaded_not_ordered_count ?? 0}
            </strong>
          </div>
          <div className="rounded-xl bg-slate-50 p-3">
            <span className="block text-xs font-bold uppercase text-slate-500">
              Quantity mismatch
            </span>
            <strong className="text-2xl">
              {summary?.quantity_mismatch_count ?? 0}
            </strong>
          </div>
        </div>
        {reconciliationExceptions.length ? (
          <div className="mt-4 space-y-2">
            {reconciliationExceptions.slice(0, 5).map((exception) => (
              <article
                className="event-reconciliation-exception rounded-xl border p-3 text-sm"
                key={exception.id}
              >
                <strong className="event-reconciliation-exception-title capitalize">
                  {statusLabel(exception.exception_type)}
                </strong>
                <p className="event-reconciliation-exception-description mt-1">
                  {exception.description}
                </p>
                <span className="event-reconciliation-exception-reference mt-1 block text-xs">
                  Reference {exception.reference_id ?? "N/A"}
                </span>
              </article>
            ))}
            {reconciliationExceptions.length > 5 ? (
              <p className="text-xs text-slate-500">
                {reconciliationExceptions.length - 5} more reconciliation
                exception
                {reconciliationExceptions.length - 5 === 1 ? "" : "s"} in the
                exception list below.
              </p>
            ) : null}
          </div>
        ) : (
          <p className="mt-4 rounded-xl border border-dashed bg-slate-50 p-4 text-sm text-slate-500">
            No released order/loadout mismatches detected.
          </p>
        )}
      </section>

      <section className="mt-5 rounded-2xl border bg-white p-4">
        <p className="brand-eyebrow">Decision packet</p>
        <h4 className="font-bold">Approval and closeout evidence</h4>
        <p className="mt-1 text-sm text-slate-600">
          Settlement approval and closure are recorded as durable closeout
          evidence for Purchasing, Reconciliation, and leadership review.
        </p>
        <div className="mt-4 grid gap-3 text-sm md:grid-cols-2">
          <div className="rounded-xl bg-slate-50 p-3">
            <span className="block text-xs font-bold uppercase text-slate-500">
              Approved
            </span>
            {summary?.approved_at ? (
              <>
                {displayDateTime(summary.approved_at)} by{" "}
                {summary.approved_by ?? "unknown"}
              </>
            ) : (
              "Not approved"
            )}
          </div>
          <div className="rounded-xl bg-slate-50 p-3">
            <span className="block text-xs font-bold uppercase text-slate-500">
              Closed
            </span>
            {summary?.closed_at ? (
              <>
                {displayDateTime(summary.closed_at)} by{" "}
                {summary.closed_by ?? "unknown"}
              </>
            ) : (
              "Not closed"
            )}
          </div>
          <div className="rounded-xl bg-slate-50 p-3 md:col-span-2">
            <span className="block text-xs font-bold uppercase text-slate-500">
              Settlement notes
            </span>
            {summary?.notes || "No settlement notes recorded."}
          </div>
        </div>
      </section>

      {!readOnly ? (
        <form
          className="mt-5 grid gap-3 rounded-2xl border bg-slate-50 p-4 md:grid-cols-2"
          onSubmit={(event) => void saveSettlement(event)}
        >
          <div className="md:col-span-2">
            <p className="brand-eyebrow">Settlement control</p>
            <h4 className="font-bold">Configure closeout status</h4>
            <p className="text-sm text-slate-600">
              Use this as the admin closeout checkpoint after order review and
              store loadout are complete. Approved and closed statuses require
              100% readiness with no open exceptions.
            </p>
          </div>
          <label className="grid gap-1 text-sm font-semibold">
            Status
            <select
              className="rounded-lg border p-2"
              defaultValue={summary?.status ?? "draft"}
              key={summary?.status ?? "draft"}
              name="status"
            >
              {settlementStatuses.map((status) => (
                <option key={status.value} value={status.value}>
                  {status.label}
                </option>
              ))}
            </select>
          </label>
          <label className="grid gap-1 text-sm font-semibold md:col-span-2">
            Settlement notes
            <textarea
              className="min-h-20 rounded-lg border p-2"
              name="notes"
              placeholder="Final settlement notes, remaining manual approvals, or finance handoff details."
            />
          </label>
          <button
            className="rounded-xl bg-slate-950 px-4 py-2 font-bold text-white disabled:bg-slate-400 md:col-span-2"
            disabled={busy}
            type="submit"
          >
            Save settlement status
          </button>
        </form>
      ) : null}

      <section className="mt-5 rounded-2xl border bg-white p-4">
        <p className="brand-eyebrow">Reports / Exports</p>
        <h4 className="font-bold">Settlement exports</h4>
        <p className="mt-1 text-sm text-slate-600">
          Download finance-ready closeout files for orders, loadout completion,
          exceptions, and audit activity.
        </p>
        {archivedBackup ? (
          <div className="event-semantic-success mt-4 rounded-xl border p-3 text-sm">
            <strong className="block">Immutable closeout archive</strong>
            <span className="block">
              {archivedBackup.filename} ·{" "}
              {(archivedBackup.size_bytes / 1024).toFixed(1)} KB ·{" "}
              {new Date(archivedBackup.created_at).toLocaleString()}
            </span>
            <span className="mt-1 block break-all font-mono text-xs">
              SHA-256: {archivedBackup.sha256}
            </span>
            <span className="block text-xs">
              Created by {archivedBackup.created_by}
            </span>
          </div>
        ) : null}
        <div className="mt-4 flex flex-wrap gap-2">
          {summary?.status === "closed" ? (
            <button
              className="rounded-lg bg-green-800 px-3 py-2 text-sm font-bold text-white disabled:bg-slate-400"
              disabled={busy}
              onClick={() => void downloadArchivedBackup()}
              type="button"
            >
              Download archived closeout backup
            </button>
          ) : null}
          <button
            className="rounded-lg bg-blue-800 px-3 py-2 text-sm font-bold text-white disabled:bg-slate-400"
            disabled={busy}
            onClick={() => void downloadOrderBackup()}
            type="button"
          >
            Complete order backup (.xlsx)
          </button>
          {exportReports.map((report) => (
            <button
              className="rounded-lg border px-3 py-2 text-sm font-bold disabled:bg-slate-100"
              disabled={busy}
              key={report.type}
              onClick={() => void downloadReport(report.type)}
              type="button"
            >
              {report.label}
            </button>
          ))}
        </div>
      </section>

      {!readOnly ? (
        <form
          className="mt-5 grid gap-3 rounded-2xl border bg-slate-50 p-4 md:grid-cols-3"
          onSubmit={(event) => void createException(event)}
        >
          <div className="md:col-span-3">
            <p className="brand-eyebrow">Exception workflow</p>
            <h4 className="font-bold">Add manual settlement exception</h4>
            <p className="text-sm text-slate-600">
              Track finance, paperwork, or operational issues that are not
              created automatically by order and loadout checks.
            </p>
          </div>
          <label className="grid gap-1 text-sm font-semibold">
            Type
            <select
              className="rounded-lg border p-2"
              name="exception_type"
              required
            >
              <option value="finance_review">Finance review</option>
              <option value="paperwork_missing">Paperwork missing</option>
              <option value="manual_adjustment">Manual adjustment</option>
              <option value="vendor_followup">Vendor follow-up</option>
              <option value="other">Other</option>
            </select>
          </label>
          <label className="grid gap-1 text-sm font-semibold">
            Severity
            <select className="rounded-lg border p-2" name="severity">
              <option value="medium">Medium</option>
              <option value="low">Low</option>
              <option value="high">High</option>
            </select>
          </label>
          <label className="grid gap-1 text-sm font-semibold">
            Reference
            <input
              className="rounded-lg border p-2"
              name="reference_id"
              placeholder="Store, order, vendor, or note"
            />
          </label>
          <input name="reference_type" type="hidden" value="manual" />
          <label className="grid gap-1 text-sm font-semibold md:col-span-3">
            Description
            <textarea
              className="min-h-20 rounded-lg border p-2"
              name="description"
              placeholder="Describe what needs to be resolved before event settlement can close."
              required
            />
          </label>
          <button
            className="rounded-xl bg-blue-800 px-4 py-2 font-bold text-white disabled:bg-slate-400 md:col-span-3"
            disabled={busy}
            type="submit"
          >
            Add settlement exception
          </button>
        </form>
      ) : null}

      <section className="mt-5 overflow-x-auto rounded-xl border bg-white">
        <div className="min-w-[900px]">
          <div className="grid grid-cols-[0.8fr_0.6fr_0.6fr_0.8fr_1.3fr_0.7fr] gap-3 bg-slate-50 p-3 text-xs font-bold uppercase text-slate-500">
            <span>Type</span>
            <span>Severity</span>
            <span>Status</span>
            <span>Reference</span>
            <span>Description</span>
            <span>Action</span>
          </div>
          {summary?.exceptions.map((exception) => (
            <article
              className="grid grid-cols-[0.8fr_0.6fr_0.6fr_0.8fr_1.3fr_0.7fr] gap-3 border-t p-3 text-sm"
              key={exception.id}
            >
              <span className="capitalize">
                {statusLabel(exception.exception_type)}
              </span>
              <span className="capitalize">{exception.severity}</span>
              <span className="capitalize">
                {statusLabel(exception.status)}
              </span>
              <span>
                {exception.reference_id ?? exception.reference_type ?? "—"}
              </span>
              <span>{exception.description}</span>
              <span>
                {exception.id.startsWith("generated:") ? (
                  <span className="text-xs text-slate-500">Auto check</span>
                ) : readOnly ? (
                  <span className="text-xs font-semibold text-slate-500">
                    Read only
                  </span>
                ) : exception.status === "open" ? (
                  <button
                    className="rounded-lg bg-green-700 px-3 py-2 text-xs font-bold text-white disabled:bg-slate-400"
                    disabled={busy}
                    onClick={() => void resolveException(exception.id)}
                    type="button"
                  >
                    Resolve
                  </button>
                ) : (
                  <button
                    className="rounded-lg border px-3 py-2 text-xs font-bold disabled:bg-slate-100"
                    disabled={busy}
                    onClick={() => void reopenException(exception.id)}
                    type="button"
                  >
                    Reopen
                  </button>
                )}
              </span>
            </article>
          ))}
        </div>
        {summary && !summary.exceptions.length ? (
          <p className="border-t p-5 text-sm text-slate-500">
            No open settlement exceptions. This event is ready for final
            closeout once admin review is complete.
          </p>
        ) : null}
        {!summary ? (
          <p className="border-t p-5 text-sm text-slate-500">
            Loading settlement summary...
          </p>
        ) : null}
      </section>
    </section>
  );
}

function Metric({ label, value }: { label: string; value: number | string }) {
  return (
    <div className="rounded-xl border bg-white p-3">
      <span className="text-xs font-bold uppercase text-slate-500">
        {label}
      </span>
      <strong className="mt-1 block text-2xl">{value}</strong>
    </div>
  );
}
