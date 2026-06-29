"use client";

import { FormEvent, useEffect, useState } from "react";
import {
  AuditEventPage,
  AuditFilters,
  AuditSummary,
  downloadAuditExport,
  getAuditSummary,
  listAuditEvents,
} from "@/lib/api";
import { useAuth } from "@/lib/auth";

const pageSize = 50;

export function AuditReportingPanel() {
  const { user } = useAuth();
  const [draft, setDraft] = useState<AuditFilters>({});
  const [filters, setFilters] = useState<AuditFilters>({});
  const [page, setPage] = useState<AuditEventPage | null>(null);
  const [summary, setSummary] = useState<AuditSummary | null>(null);
  const [offset, setOffset] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  async function load(activeFilters: AuditFilters, activeOffset: number) {
    setLoading(true);
    setError(null);
    try {
      const [events, totals] = await Promise.all([
        listAuditEvents(activeFilters, pageSize, activeOffset),
        getAuditSummary(activeFilters),
      ]);
      setPage(events);
      setSummary(totals);
    } catch (reason) {
      setError(
        reason instanceof Error
          ? reason.message
          : "Unable to load audit records.",
      );
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load(filters, offset);
  }, [filters, offset]);

  function search(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setOffset(0);
    setFilters(draft);
  }

  function clear() {
    setDraft({});
    setOffset(0);
    setFilters({});
  }

  async function exportCsv() {
    try {
      const blob = await downloadAuditExport(filters);
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = "btsp-audit.csv";
      link.click();
      URL.revokeObjectURL(url);
    } catch (reason) {
      setError(
        reason instanceof Error
          ? reason.message
          : "Unable to export audit records.",
      );
    }
  }

  return (
    <div>
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold">Audit reporting</h2>
          <p className="mt-2 text-sm text-slate-600">
            Search the immutable event ledger by actor, entity, event, and time
            window.
          </p>
        </div>
        {user?.permissions.includes("audit.export") ? (
          <button
            className="rounded border px-4 py-2 text-sm"
            onClick={() => void exportCsv()}
            type="button"
          >
            Export CSV
          </button>
        ) : null}
      </div>

      <form
        className="mt-6 grid gap-3 rounded border bg-slate-50 p-4 md:grid-cols-3"
        onSubmit={search}
      >
        {(["event_type", "entity_type", "entity_id", "actor"] as const).map(
          (key) => (
            <label className="text-sm font-medium" key={key}>
              {key.replaceAll("_", " ")}
              <input
                className="mt-1 w-full rounded border bg-white px-3 py-2"
                onChange={(event) =>
                  setDraft((current) => ({
                    ...current,
                    [key]: event.target.value,
                  }))
                }
                value={draft[key] ?? ""}
              />
            </label>
          ),
        )}
        <label className="text-sm font-medium">
          From
          <input
            className="mt-1 w-full rounded border bg-white px-3 py-2"
            onChange={(event) =>
              setDraft((current) => ({
                ...current,
                date_from: event.target.value
                  ? new Date(event.target.value).toISOString()
                  : undefined,
              }))
            }
            type="datetime-local"
            value={draft.date_from?.slice(0, 16) ?? ""}
          />
        </label>
        <label className="text-sm font-medium">
          To
          <input
            className="mt-1 w-full rounded border bg-white px-3 py-2"
            onChange={(event) =>
              setDraft((current) => ({
                ...current,
                date_to: event.target.value
                  ? new Date(event.target.value).toISOString()
                  : undefined,
              }))
            }
            type="datetime-local"
            value={draft.date_to?.slice(0, 16) ?? ""}
          />
        </label>
        <div className="flex gap-2 md:col-span-3">
          <button
            className="rounded bg-slate-900 px-4 py-2 text-sm text-white"
            type="submit"
          >
            Search
          </button>
          <button
            className="rounded border bg-white px-4 py-2 text-sm"
            onClick={clear}
            type="button"
          >
            Clear
          </button>
        </div>
      </form>

      {error ? (
        <p className="mt-4 rounded bg-red-50 p-3 text-sm text-red-700">
          {error}
        </p>
      ) : null}
      {summary ? (
        <section className="mt-6 grid gap-3 md:grid-cols-4">
          <article className="rounded border p-4">
            <p className="text-sm text-slate-500">Total events</p>
            <p className="text-3xl font-bold">{summary.total}</p>
          </article>
          {[summary.event_types, summary.entity_types, summary.actors].map(
            (items, index) => (
              <article className="rounded border p-4" key={index}>
                <p className="text-sm text-slate-500">
                  Top {index === 0 ? "event" : index === 1 ? "entity" : "actor"}
                </p>
                <p className="truncate font-semibold">
                  {items[0]?.key ?? "None"}
                </p>
                <p className="text-sm text-slate-500">
                  {items[0]?.count ?? 0} events
                </p>
              </article>
            ),
          )}
        </section>
      ) : null}

      <div className="mt-6 overflow-x-auto rounded border">
        <table className="w-full text-left text-sm">
          <thead className="bg-slate-100">
            <tr>
              <th className="p-3">Time</th>
              <th className="p-3">Event</th>
              <th className="p-3">Entity</th>
              <th className="p-3">Actor</th>
              <th className="p-3">Evidence</th>
            </tr>
          </thead>
          <tbody>
            {page?.items.map((item) => (
              <tr className="border-t align-top" key={item.id}>
                <td className="whitespace-nowrap p-3">
                  {new Date(item.created_at).toLocaleString()}
                </td>
                <td className="p-3 font-medium">{item.event_type}</td>
                <td className="p-3">
                  {item.entity_type}
                  <span className="block text-xs text-slate-500">
                    {item.entity_id}
                  </span>
                </td>
                <td className="p-3">{item.actor}</td>
                <td className="p-3">
                  <details>
                    <summary className="cursor-pointer">Payload</summary>
                    <pre className="mt-2 max-w-md overflow-auto rounded bg-slate-950 p-2 text-xs text-white">
                      {JSON.stringify(item.payload, null, 2)}
                    </pre>
                  </details>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="mt-4 flex items-center justify-between text-sm">
        <span>
          {loading
            ? "Loading…"
            : page
              ? `${page.offset + 1}–${Math.min(page.offset + page.items.length, page.total)} of ${page.total}`
              : "No records"}
        </span>
        <div className="flex gap-2">
          <button
            className="rounded border px-3 py-1"
            disabled={offset === 0 || loading}
            onClick={() => setOffset(Math.max(0, offset - pageSize))}
            type="button"
          >
            Previous
          </button>
          <button
            className="rounded border px-3 py-1"
            disabled={!page || offset + pageSize >= page.total || loading}
            onClick={() => setOffset(offset + pageSize)}
            type="button"
          >
            Next
          </button>
        </div>
      </div>
    </div>
  );
}
