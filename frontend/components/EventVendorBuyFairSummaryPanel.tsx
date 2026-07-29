"use client";

import { useEffect, useState } from "react";
import {
  downloadEventBuyFairOrders,
  downloadSubEventBuyFairOrders,
  EventBuyFairSummary,
  getEventBuyFairSummary,
  getSubEventBuyFairSummary,
} from "@/lib/event-buy-fair-api";

const money = (value: string) =>
  Number(value).toLocaleString([], { style: "currency", currency: "USD" });

export function EventVendorBuyFairSummaryPanel({
  eventId,
  subEventId,
  subEventName,
}: {
  eventId?: string;
  subEventId?: string;
  subEventName?: string;
}) {
  const [summary, setSummary] = useState<EventBuyFairSummary | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [showOrders, setShowOrders] = useState(false);

  useEffect(() => {
    const request = subEventId
      ? getSubEventBuyFairSummary(subEventId)
      : eventId
        ? getEventBuyFairSummary(eventId)
        : Promise.resolve(null);
    void request
      .then(setSummary)
      .catch((caught: unknown) =>
        setError(
          caught instanceof Error
            ? caught.message
            : "Buy fair totals could not load",
        ),
      );
  }, [eventId, subEventId]);

  const subEventScoped = Boolean(subEventId);

  return (
    <section className="event-ui rounded-2xl border bg-white p-5">
      <p className="brand-eyebrow">Vendor buy fair</p>
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h3 className="text-xl font-bold">
            {subEventScoped
              ? `${subEventName ?? "Current event"} order volume`
              : "Event order volume"}
          </h3>
          <p className="text-sm text-slate-600">
            Draft and submitted orders across all vendors in this{" "}
            {subEventScoped ? (subEventName ?? "current event") : "event"}.
          </p>
        </div>
        <button
          className="rounded-xl border px-4 py-2 font-bold"
          onClick={() =>
            void (subEventId
              ? downloadSubEventBuyFairOrders(subEventId)
              : eventId
                ? downloadEventBuyFairOrders(eventId)
                : Promise.resolve())
          }
          type="button"
        >
          Export {subEventScoped ? (subEventName ?? "current event") : "event"}{" "}
          orders
        </button>
      </div>
      {error ? (
        <p className="mt-3 rounded-xl bg-red-50 p-3 text-red-800">{error}</p>
      ) : null}
      {summary ? (
        <div className="mt-4 grid gap-3 sm:grid-cols-3 lg:grid-cols-6">
          {[
            ["Vendors", summary.vendor_count],
            ["Orders", summary.order_count],
            ["Drafts", summary.draft_count],
            ["Submitted", summary.submitted_count],
            ["Units", summary.total_units],
            ["Volume", money(summary.total_volume)],
          ].map(([label, value]) => (
            <div className="rounded-xl bg-slate-50 p-3" key={label}>
              <span className="block text-xs font-bold uppercase text-slate-500">
                {label}
              </span>
              <strong className="text-lg">{value}</strong>
            </div>
          ))}
        </div>
      ) : null}
      {summary?.vendors.length ? (
        <div className="mt-5 overflow-x-auto">
          <h4 className="mb-2 font-bold">Vendor performance</h4>
          <table className="w-full min-w-[680px] text-left text-sm">
            <thead className="border-b text-xs uppercase text-slate-500">
              <tr>
                <th className="p-2">Vendor</th>
                <th className="p-2">Orders</th>
                <th className="p-2">Drafts</th>
                <th className="p-2">Submitted</th>
                <th className="p-2">Units</th>
                <th className="p-2">Volume</th>
              </tr>
            </thead>
            <tbody>
              {summary.vendors.map((vendor) => (
                <tr className="border-b" key={vendor.vendor_code}>
                  <td className="p-2 font-bold">{vendor.vendor_code}</td>
                  <td className="p-2">{vendor.order_count}</td>
                  <td className="p-2">{vendor.draft_count}</td>
                  <td className="p-2">{vendor.submitted_count}</td>
                  <td className="p-2">{vendor.total_units}</td>
                  <td className="p-2">{money(vendor.total_volume)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}
      {summary?.orders.length ? (
        <div className="mt-4">
          <button
            className="text-sm font-bold text-blue-800"
            onClick={() => setShowOrders((current) => !current)}
            type="button"
          >
            {showOrders
              ? "Hide order detail"
              : `Show ${summary.orders.length} order${summary.orders.length === 1 ? "" : "s"}`}
          </button>
          {showOrders ? (
            <div className="mt-2 max-h-80 space-y-2 overflow-auto">
              {summary.orders.map((order) => (
                <div
                  className="grid gap-1 rounded-xl bg-slate-50 p-3 text-sm sm:grid-cols-[1fr_100px_140px_120px]"
                  key={order.id}
                >
                  <strong className="break-words">{order.order_number}</strong>
                  <span>Store {order.store_number}</span>
                  <span>{order.status.replaceAll("_", " ")}</span>
                  <span className="font-bold">{money(order.total_volume)}</span>
                </div>
              ))}
            </div>
          ) : null}
        </div>
      ) : null}
      <p className="mt-3 text-xs text-slate-500">
        Submitted orders automatically appear in the standard Purchasing review
        queue. Vendors open the branded buying workspace from their event
        landing page.
      </p>
    </section>
  );
}
