"use client";

import { useEffect, useState } from "react";
import {
  getEventLiveInsights,
  EventLiveInsights,
} from "@/lib/event-live-insights-api";
import { listMyEvents } from "@/lib/event-admin-api";
import { subscribeEventRealtime } from "@/lib/event-realtime";

export function EventLiveInsightsLanding({
  subEventId,
}: {
  subEventId?: string;
} = {}) {
  const [insights, setInsights] = useState<EventLiveInsights[]>([]);

  useEffect(() => {
    let active = true;
    let unsubscribers: Array<() => void> = [];
    let timer = 0;
    async function connect() {
      const subEvents = subEventId
        ? [{ id: subEventId }]
        : (await listMyEvents()).flatMap((event) =>
            event.sub_events.filter((item) =>
              item.module_codes.includes("live-display"),
            ),
          );
      const refresh = async () => {
        const values = await Promise.all(
          subEvents.map((item) =>
            getEventLiveInsights(item.id).catch(() => null),
          ),
        );
        if (active)
          setInsights(
            values.filter((item): item is EventLiveInsights => item !== null),
          );
      };
      await refresh();
      unsubscribers = subEvents.map((item) =>
        subscribeEventRealtime(item.id, refresh),
      );
      timer = window.setInterval(refresh, 15_000);
    }
    void connect().catch(() => setInsights([]));
    return () => {
      active = false;
      unsubscribers.forEach((unsubscribe) => unsubscribe());
      if (timer) window.clearInterval(timer);
    };
  }, [subEventId]);

  if (!insights.length) return null;
  return (
    <section className="event-ui mb-6 space-y-4 rounded-2xl border border-blue-400/30 bg-slate-950 p-5 text-white">
      <div>
        <p className="brand-eyebrow">Live buying intelligence</p>
        <h2 className="text-2xl font-bold">Live Event Summary</h2>
      </div>
      {insights.map((item) => (
        <article
          className="rounded-xl border border-slate-700 p-4"
          key={item.sub_event_id}
        >
          <div className="flex flex-wrap justify-between gap-3">
            <div>
              <strong>{item.sub_event_name}</strong>
              <p className="text-sm text-slate-400">{item.event_name}</p>
            </div>
            <span
              className={
                item.ordering_status === "open"
                  ? "text-green-400"
                  : "text-amber-300"
              }
            >
              {item.ordering_status === "open"
                ? "ORDERS LIVE"
                : "ORDERING CLOSED"}
            </span>
          </div>
          {item.scope === "vendor" ? (
            <div className="mt-4 grid gap-3 sm:grid-cols-2">
              <Metric
                label={`${
                  item.vendor_totals.length > 1
                    ? "All represented vendors"
                    : (item.vendor_totals[0]?.vendor_name ??
                      item.vendor_name ??
                      item.vendor_code ??
                      "Vendor")
                } ${item.sub_event_name} Total`}
                value={`$${item.vendor_sub_event_spend}`}
              />
              <Metric
                label="Next represented model"
                value={
                  item.slides_until_next_product === null
                    ? "No later models"
                    : `${item.slides_until_next_product} slide${
                        item.slides_until_next_product === 1 ? "" : "s"
                      } · ${item.next_vendor_name ?? item.next_vendor_code ?? "Vendor"}`
                }
              />
            </div>
          ) : (
            <div className="mt-4 grid gap-3 sm:grid-cols-3">
              <Metric
                label={`${item.sub_event_name} Total`}
                value={`$${item.sub_event_spend}`}
              />
              <Metric
                label="Units ordered"
                value={String(item.sub_event_units)}
              />
              <Metric
                label="Entities ordering"
                value={String(item.responding_entities)}
              />
            </div>
          )}
          {item.scope === "vendor" ? (
            <div className="mt-4">
              {item.vendor_totals.length > 1 ? (
                <div className="mb-4">
                  <h3 className="font-bold">Performance by vendor</h3>
                  <div className="mt-2 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                    {item.vendor_totals.map((vendor) => (
                      <Metric
                        key={vendor.vendor_code}
                        label={vendor.vendor_name}
                        value={`$${vendor.committed_spend} · ${vendor.units_ordered} units`}
                      />
                    ))}
                  </div>
                </div>
              ) : null}
              <div className="event-live-product-table mt-3 overflow-x-auto">
                <table className="w-full text-left text-sm">
                  <thead>
                    <tr className="text-slate-400">
                      <th>Position</th>
                      {item.vendor_totals.length > 1 ? <th>Vendor</th> : null}
                      <th>Model</th>
                      <th>Units</th>
                      <th>Spend</th>
                    </tr>
                  </thead>
                  <tbody>
                    {item.vendor_products.map((product) => (
                      <tr
                        className="border-t border-slate-800"
                        key={product.slide_id}
                      >
                        <td className="py-2">{product.position}</td>
                        {item.vendor_totals.length > 1 ? (
                          <td>{product.vendor_name}</td>
                        ) : null}
                        <td>
                          {product.model_number} · {product.name}
                        </td>
                        <td>{product.units_ordered}</td>
                        <td>${product.committed_spend}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <div className="event-live-product-cards mt-3">
                {item.vendor_products.map((product) => (
                  <article
                    className="event-live-product-card"
                    key={product.slide_id}
                  >
                    <div className="event-live-product-card-heading">
                      <div>
                        <span>Position {product.position}</span>
                        <strong>{product.model_number}</strong>
                      </div>
                      <strong>${product.committed_spend}</strong>
                    </div>
                    <p>{product.name}</p>
                    <div className="event-live-product-card-details">
                      {item.vendor_totals.length > 1 ? (
                        <span>{product.vendor_name}</span>
                      ) : null}
                      <span>{product.units_ordered} units</span>
                    </div>
                  </article>
                ))}
              </div>
            </div>
          ) : null}
          {item.scope === "franchise" ? (
            <div className="mt-4 grid gap-3 sm:grid-cols-3">
              <Metric
                label="Your entity"
                value={item.entity_code ?? "Assigned entity"}
              />
              <Metric
                label="Your committed units"
                value={String(item.franchise_sub_event_units)}
              />
              <Metric
                label={`Your ${item.sub_event_name} commitment`}
                value={`$${item.franchise_sub_event_spend}`}
              />
            </div>
          ) : null}
        </article>
      ))}
    </section>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="event-summary-metric rounded-xl bg-slate-900 p-3 !text-black">
      <span className="block text-xs font-bold uppercase !text-black">
        {label}
      </span>
      <strong className="mt-1 block text-xl !text-black">{value}</strong>
    </div>
  );
}
