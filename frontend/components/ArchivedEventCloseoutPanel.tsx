"use client";

import { useEffect, useState } from "react";
import { useAuth } from "@/lib/auth";
import { ManagedEvent } from "@/lib/event-admin-api";
import {
  downloadArchivedEventOrderBackup,
  EventOrderBackupArtifact,
  exportEventOrderBackup,
  getArchivedEventOrderBackup,
} from "@/lib/event-order-review-api";
import {
  EventSettlementExportReport,
  EventSettlementSummary,
  exportEventSettlementReport,
  getEventSettlementSummary,
} from "@/lib/event-settlement-api";
import { hasPermission } from "@/lib/permissions";

const money = (value: string) =>
  Number(value || "0").toLocaleString([], {
    style: "currency",
    currency: "USD",
  });

const dateTime = (value: string | null) =>
  value ? new Date(value).toLocaleString() : "Not recorded";

export function ArchivedEventCloseoutPanel({ event }: { event: ManagedEvent }) {
  const { user } = useAuth();
  const canRead = Boolean(user && hasPermission(user, "event_settlement.read"));
  const canExport = Boolean(
    user && hasPermission(user, "event_settlement.export"),
  );
  const [summary, setSummary] = useState<EventSettlementSummary | null>(null);
  const [artifact, setArtifact] = useState<EventOrderBackupArtifact | null>(
    null,
  );
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setSummary(null);
    setArtifact(null);
    setMessage(null);
    setError(null);
    if (!canRead) return;
    void Promise.all([
      getEventSettlementSummary(event.id),
      getArchivedEventOrderBackup(event.id).catch(() => null),
    ])
      .then(([nextSummary, nextArtifact]) => {
        setSummary(nextSummary);
        setArtifact(nextArtifact);
      })
      .catch((caught: unknown) =>
        setError(
          caught instanceof Error
            ? caught.message
            : "Closeout reference could not load",
        ),
      );
  }, [canRead, event.id]);

  async function download(work: () => Promise<void>, success: string) {
    setBusy(true);
    setMessage(null);
    setError(null);
    try {
      await work();
      setMessage(success);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Download failed");
    } finally {
      setBusy(false);
    }
  }

  if (!canRead) return null;

  const report = (type: EventSettlementExportReport, label: string) =>
    download(
      () => exportEventSettlementReport(event.id, type),
      `${label} downloaded.`,
    );

  return (
    <section className="event-glass-pane rounded-2xl border p-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="brand-eyebrow">Closeout reference</p>
          <h3 className="text-xl font-bold">Final operational record</h3>
          <p className="mt-1 text-sm text-slate-400">
            Read-only settlement evidence and retained event exports.
          </p>
        </div>
        <span className="rounded-full border px-3 py-2 text-sm font-bold uppercase">
          {summary?.status.replaceAll("_", " ") ?? "Loading"}
        </span>
      </div>

      {error ? (
        <p className="mt-4 rounded-xl bg-red-50 p-3 text-red-800">{error}</p>
      ) : null}
      {message ? (
        <p className="mt-4 rounded-xl bg-green-50 p-3 text-green-800">
          {message}
        </p>
      ) : null}

      <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
        <Metric
          label="Orders released"
          value={`${summary?.order_released ?? 0}/${summary?.order_total ?? 0}`}
        />
        <Metric
          label="Approved units"
          value={String(summary?.approved_units ?? 0)}
        />
        <Metric
          label="Approved spend"
          value={money(summary?.approved_spend ?? "0")}
        />
        <Metric
          label="Stores released"
          value={`${summary?.loadout_released ?? 0}/${summary?.loadout_assignment_total ?? 0}`}
        />
        <Metric
          label="Open exceptions"
          value={String(summary?.open_exception_count ?? 0)}
        />
      </div>

      <div className="mt-4 grid gap-3 text-sm sm:grid-cols-2">
        <div className="rounded-xl border border-white/10 bg-slate-950/35 p-3">
          <span className="block text-xs font-bold uppercase text-slate-400">
            Approved
          </span>
          {dateTime(summary?.approved_at ?? null)}
          {summary?.approved_by ? ` by ${summary.approved_by}` : ""}
        </div>
        <div className="rounded-xl border border-white/10 bg-slate-950/35 p-3">
          <span className="block text-xs font-bold uppercase text-slate-400">
            Closed
          </span>
          {dateTime(summary?.closed_at ?? null)}
          {summary?.closed_by ? ` by ${summary.closed_by}` : ""}
        </div>
      </div>

      {artifact ? (
        <div className="mt-4 rounded-xl border border-green-500/30 bg-green-950/25 p-3 text-sm">
          <strong className="block text-green-300">
            Immutable order backup
          </strong>
          <span className="block break-words">
            {artifact.filename} · {(artifact.size_bytes / 1024).toFixed(1)} KB
          </span>
          <span className="mt-1 block break-all font-mono text-xs text-slate-400">
            SHA-256: {artifact.sha256}
          </span>
        </div>
      ) : null}

      {canExport ? (
        <div className="mt-4 flex flex-wrap gap-2">
          {artifact ? (
            <button
              className="rounded-lg bg-green-800 px-3 py-2 text-sm font-bold text-white"
              disabled={busy}
              onClick={() =>
                void download(
                  () => downloadArchivedEventOrderBackup(event.id, event.name),
                  "Archived order backup downloaded.",
                )
              }
              type="button"
            >
              Archived order backup (.xlsx)
            </button>
          ) : (
            <button
              className="rounded-lg bg-blue-800 px-3 py-2 text-sm font-bold text-white"
              disabled={busy}
              onClick={() =>
                void download(
                  () => exportEventOrderBackup(event.id, event.name),
                  "Order backup downloaded.",
                )
              }
              type="button"
            >
              Order backup (.xlsx)
            </button>
          )}
          <ExportButton
            busy={busy}
            label="Closeout packet"
            onClick={() => void report("closeout-packet", "Closeout packet")}
          />
          <ExportButton
            busy={busy}
            label="Exception report"
            onClick={() => void report("exceptions", "Exception report")}
          />
          <ExportButton
            busy={busy}
            label="Reconciliation detail"
            onClick={() =>
              void report("reconciliation-detail", "Reconciliation detail")
            }
          />
          <ExportButton
            busy={busy}
            label="Order closeout"
            onClick={() => void report("order-closeout", "Order closeout")}
          />
          <ExportButton
            busy={busy}
            label="Loadout closeout"
            onClick={() => void report("loadout-closeout", "Loadout closeout")}
          />
          <ExportButton
            busy={busy}
            label="Audit log"
            onClick={() => void report("audit-log", "Audit log")}
          />
          <ExportButton
            busy={busy}
            label="Feedback report"
            onClick={() => void report("feedback", "Feedback report")}
          />
        </div>
      ) : null}
    </section>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl border border-white/10 bg-slate-950/35 p-3">
      <span className="block text-xs font-bold uppercase text-slate-400">
        {label}
      </span>
      <strong className="mt-1 block text-xl">{value}</strong>
    </div>
  );
}

function ExportButton({
  busy,
  label,
  onClick,
}: {
  busy: boolean;
  label: string;
  onClick: () => void;
}) {
  return (
    <button
      className="rounded-lg border px-3 py-2 text-sm font-bold"
      disabled={busy}
      onClick={onClick}
      type="button"
    >
      {label}
    </button>
  );
}
