"use client";

import { useEffect, useState } from "react";
import { useEventBranding } from "@/components/EventBrandingProvider";
import { listMyEvents } from "@/lib/event-admin-api";
import {
  EventCloseoutInsights,
  getEventCloseoutInsights,
} from "@/lib/event-closeout-insights-api";

function currency(value: string) {
  return Number(value || 0).toLocaleString([], {
    style: "currency",
    currency: "USD",
  });
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl border border-white/15 bg-black/20 p-3">
      <span className="block text-xs font-bold uppercase opacity-70">
        {label}
      </span>
      <strong className="mt-1 block text-xl">{value}</strong>
    </div>
  );
}

export function EventCloseoutInsightsLanding() {
  const { brandedClassName, brandedStyle } = useEventBranding();
  const [insights, setInsights] = useState<EventCloseoutInsights[]>([]);

  useEffect(() => {
    let active = true;
    const refresh = async () => {
      const events = await listMyEvents();
      const executiveEvents = events.filter(
        (event) =>
          event.memberships.some((membership) =>
            ["executive", "admin"].includes(membership.membership_type),
          ) &&
          event.sub_events.some((subEvent) =>
            subEvent.module_codes.includes("event-settlement"),
          ),
      );
      const values = await Promise.all(
        executiveEvents.map((event) =>
          getEventCloseoutInsights(event.id).catch(() => null),
        ),
      );
      if (active) {
        setInsights(
          values.filter((item): item is EventCloseoutInsights => item !== null),
        );
      }
    };
    void refresh().catch(() => setInsights([]));
    const timer = window.setInterval(() => void refresh(), 30_000);
    return () => {
      active = false;
      window.clearInterval(timer);
    };
  }, []);

  if (!insights.length) return null;
  const totalSpend = insights.reduce(
    (sum, item) => sum + Number(item.approved_spend || 0),
    0,
  );
  const averageReadiness =
    insights.reduce((sum, item) => sum + Number(item.readiness_percentage), 0) /
    insights.length;
  const rated = insights.filter((item) => item.feedback_average_rating != null);
  const averageRating = rated.length
    ? rated.reduce(
        (sum, item) => sum + Number(item.feedback_average_rating),
        0,
      ) / rated.length
    : null;
  const averageConversion =
    insights.reduce(
      (sum, item) => sum + Number(item.order_to_loadout_rate),
      0,
    ) / insights.length;
  function downloadBenchmark() {
    const header = [
      "event",
      "status",
      "readiness",
      "approved_spend",
      "order_to_loadout",
      "feedback_response_rate",
      "feedback_average_rating",
    ];
    const rows = insights.map((item) => [
      item.event_name,
      item.status,
      item.readiness_percentage,
      item.approved_spend,
      item.order_to_loadout_rate,
      item.feedback_response_rate,
      item.feedback_average_rating ?? "",
    ]);
    const csv = [header, ...rows]
      .map((row) =>
        row
          .map((value) => `"${String(value).replaceAll('"', '""')}"`)
          .join(","),
      )
      .join("\n");
    const url = URL.createObjectURL(
      new Blob([csv], { type: "text/csv;charset=utf-8" }),
    );
    const link = document.createElement("a");
    link.href = url;
    link.download = "event-benchmarking.csv";
    link.click();
    URL.revokeObjectURL(url);
  }
  return (
    <section className="event-ui mb-6 space-y-4">
      <div>
        <p className="brand-eyebrow">Executive closeout</p>
        <h2 className="text-2xl font-bold">Event settlement overview</h2>
      </div>
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <Metric label="Shows tracked" value={String(insights.length)} />
        <Metric
          label="Combined approved spend"
          value={currency(String(totalSpend))}
        />
        <Metric
          label="Average readiness"
          value={`${averageReadiness.toFixed(0)}%`}
        />
        <Metric
          label="Average feedback"
          value={
            averageRating == null ? "—" : `${averageRating.toFixed(1)} / 5`
          }
        />
        <Metric
          label="Avg. order-to-loadout"
          value={`${averageConversion.toFixed(0)}%`}
        />
      </div>
      <button
        className="brand-button"
        onClick={downloadBenchmark}
        type="button"
      >
        Download benchmark CSV
      </button>
      {insights.map((item) => (
        <article
          className={brandedClassName(
            item.event_id,
            "rounded-2xl p-5 text-white",
          )}
          key={item.event_id}
          style={brandedStyle(item.event_id)}
        >
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <h3 className="text-xl font-bold">{item.event_name}</h3>
              <p className="capitalize opacity-75">
                {item.status.replaceAll("_", " ")}
              </p>
            </div>
            <strong>
              {Number(item.readiness_percentage).toFixed(0)}% ready
            </strong>
          </div>
          <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <Metric
              label="Approved spend"
              value={currency(item.approved_spend)}
            />
            <Metric
              label="Approved units"
              value={String(item.approved_units)}
            />
            <Metric
              label="Orders released"
              value={`${item.order_released} / ${item.order_total}`}
            />
            <Metric
              label="Stores released"
              value={`${item.loadout_released} / ${item.loadout_assignment_total}`}
            />
            <Metric
              label="Feedback response rate"
              value={`${Number(item.feedback_response_rate).toFixed(0)}%`}
            />
            <Metric
              label="Average feedback"
              value={
                item.feedback_average_rating == null
                  ? "—"
                  : `${Number(item.feedback_average_rating).toFixed(1)} / 5`
              }
            />
            <Metric
              label="Order-to-loadout"
              value={`${Number(item.order_to_loadout_rate).toFixed(0)}%`}
            />
          </div>
          <p className="mt-3 text-sm font-semibold">
            {item.open_exception_count
              ? `${item.open_exception_count} closeout exception${item.open_exception_count === 1 ? "" : "s"} remain open.`
              : item.vendor_hall_closeout_ready === false
                ? `Vendor Hall closeout pending (${(item.vendor_hall_status ?? "unknown").replaceAll("_", " ")}).`
                : "No open closeout exceptions."}
          </p>
        </article>
      ))}
    </section>
  );
}
