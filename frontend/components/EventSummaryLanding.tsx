"use client";

import { useEffect, useState } from "react";
import { EventSummary, getEventSummary } from "@/lib/event-summary-api";

export function EventSummaryLanding({
  eventId,
  reviewMode = false,
}: {
  eventId: string;
  reviewMode?: boolean;
}) {
  const [summary, setSummary] = useState<EventSummary | null>(null);
  const [dimension, setDimension] = useState<
    "vendors" | "entities" | "departments"
  >("vendors");
  useEffect(() => {
    let active = true;
    const refresh = () =>
      void getEventSummary(eventId)
        .then((value) => {
          if (active) setSummary(value);
        })
        .catch(() => undefined);
    refresh();
    const timer = window.setInterval(refresh, 15_000);
    return () => {
      active = false;
      window.clearInterval(timer);
    };
  }, [eventId]);
  if (!summary) return null;
  return (
    <section className="event-ui mt-6 rounded-2xl border border-blue-400/30 bg-slate-950 p-5 text-white">
      <p className="brand-eyebrow">Event summary</p>
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h2 className="text-2xl font-bold">{summary.event_name}</h2>
          <p className="text-sm text-slate-400">
            {summary.scope === "operations"
              ? "All entities and vendors"
              : summary.scope === "vendor"
                ? `Vendor ${summary.vendor_code}`
                : `Entity ${summary.entity_code ?? "assigned"}`}
          </p>
        </div>
        <div className="text-right">
          <span className="block text-xs uppercase text-blue-300">
            {summary.scope === "vendor"
              ? "Vendor event spend"
              : summary.scope === "buddys"
                ? "Your event spend"
                : "Total event spend"}
          </span>
          <strong className="text-3xl">${summary.total_spend}</strong>
        </div>
      </div>
      <div className="mt-4 grid gap-3 sm:grid-cols-3">
        <Metric label="Orders" value={String(summary.total_order_count)} />
        <Metric label="Units" value={String(summary.total_units)} />
        <Metric label="Event total" value={`$${summary.total_spend}`} />
      </div>
      {summary.scope === "operations" ? (
        <div className="mt-5 grid gap-5 md:grid-cols-2">
          {reviewMode ? (
            <div className="md:col-span-2">
              <label className="grid max-w-sm gap-1 text-sm font-bold">
                Review dimension
                <select
                  className="rounded-lg border p-2"
                  onChange={(event) =>
                    setDimension(event.target.value as typeof dimension)
                  }
                  value={dimension}
                >
                  <option value="vendors">By vendor</option>
                  <option value="entities">By franchise</option>
                  <option value="departments">By department</option>
                </select>
              </label>
              <div className="mt-4">
                <Breakdown
                  title={
                    dimension === "vendors"
                      ? "By vendor"
                      : dimension === "entities"
                        ? "By franchise"
                        : "By department"
                  }
                  rows={summary[dimension]}
                  totalSpend={summary.total_spend}
                />
              </div>
            </div>
          ) : (
            <>
              <Breakdown
                title="By vendor"
                rows={summary.vendors}
                totalSpend={summary.total_spend}
              />
              <Breakdown
                title="By franchise"
                rows={summary.entities}
                totalSpend={summary.total_spend}
              />
            </>
          )}
        </div>
      ) : null}
    </section>
  );
}

function Breakdown({
  title,
  rows,
  totalSpend,
}: {
  title: string;
  rows: Array<{
    code: string;
    spend: string;
    units: number;
    average_order_spend?: string;
  }>;
  totalSpend: string;
}) {
  return (
    <div>
      <h3 className="font-bold">{title}</h3>
      <div className="mt-2 space-y-2">
        {rows.map((row) => (
          <div
            className="event-summary-breakdown flex justify-between rounded-lg bg-slate-900 p-2 text-sm"
            key={row.code}
          >
            <span>
              {row.code} · {row.units} units
            </span>
            <span className="text-right">
              <strong className="block">${row.spend}</strong>
              <small className="block text-slate-400">
                {Number(totalSpend)
                  ? `${((Number(row.spend) / Number(totalSpend)) * 100).toFixed(0)}% of event`
                  : "No spend"}
              </small>
              {row.average_order_spend ? (
                <small className="text-slate-400">
                  ${row.average_order_spend} avg/order
                </small>
              ) : null}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="event-summary-metric rounded-xl bg-slate-900 p-3 !text-black">
      <span className="block text-xs uppercase !text-black">{label}</span>
      <strong className="text-xl !text-black">{value}</strong>
    </div>
  );
}
