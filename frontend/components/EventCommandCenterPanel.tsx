"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { ManagedEvent } from "@/lib/event-admin-api";
import {
  EventBuyFairSummary,
  getEventBuyFairSummary,
} from "@/lib/event-buy-fair-api";
import {
  EventOrderReviewSummary,
  getEventOrderReview,
} from "@/lib/event-order-review-api";
import {
  EventSettlementSummary,
  getEventSettlementSummary,
} from "@/lib/event-settlement-api";
import {
  getStoreLoadoutSummary,
  StoreLoadoutSummary,
} from "@/lib/store-loadout-api";
import { getVendorHallSummary, VendorHallSummary } from "@/lib/vendor-hall-api";
import {
  getVendorHallFloorMapStatus,
  VendorHallFloorMapStatus,
} from "@/lib/vendor-hall-api";
import { VendorHallLiveMap } from "@/components/VendorHallLiveMap";

const moduleNames: Record<string, string> = {
  "product-slides": "Product slides",
  "live-display": "Live display",
  ordering: "Ordering",
  polling: "Polling",
  "check-in": "Check-in",
  "staff-tasks": "Staff tasks",
  "vendor-booths": "Vendor booths",
  "vendor-hall-setup": "Vendor hall",
  "vendor-hall-inventory": "Vendor inventory",
  "event-inventory": "Event inventory",
  "store-loadout": "Store loadout",
  "event-settlement": "Settlement",
  "vendor-buy-fair": "Vendor buy fair",
};

type CommandCenterState = {
  orders: EventOrderReviewSummary | null;
  vendorHall: VendorHallSummary | null;
  vendorMap: VendorHallFloorMapStatus | null;
  loadout: StoreLoadoutSummary | null;
  settlement: EventSettlementSummary | null;
  buyFair: EventBuyFairSummary | null;
};

type AttentionItem = {
  title: string;
  detail: string;
  severity: "critical" | "warning" | "setup";
  actionLabel: string;
  onAction: () => void;
};

type CsvRow = Array<number | string>;
type AttentionFilter = "all" | AttentionItem["severity"];

function numericValue(value: number | string | null | undefined) {
  return Number(value ?? 0);
}

function formatCurrency(value: string | null | undefined) {
  return Number(value || "0").toLocaleString([], {
    style: "currency",
    currency: "USD",
  });
}

function statusLabel(value: string) {
  return value.replaceAll("_", " ");
}

function uniqueModules(event: ManagedEvent) {
  return Array.from(
    new Set(event.sub_events.flatMap((subEvent) => subEvent.module_codes)),
  );
}

function csvCell(value: number | string) {
  const text = String(value);
  return /[",\n]/.test(text) ? `"${text.replaceAll('"', '""')}"` : text;
}

function downloadCsv(filename: string, rows: CsvRow[]) {
  const content = rows.map((row) => row.map(csvCell).join(",")).join("\n");
  const blob = new Blob([content], { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  URL.revokeObjectURL(url);
}

export function EventCommandCenterPanel({
  event,
  onOpenModule,
  onOpenOrders,
  onOpenSetup,
  onOpenSubEvent,
}: {
  event: ManagedEvent;
  onOpenModule: (moduleCode: string) => void;
  onOpenOrders: () => void;
  onOpenSetup: () => void;
  onOpenSubEvent: (subEventId: string) => void;
}) {
  const [state, setState] = useState<CommandCenterState>({
    orders: null,
    vendorHall: null,
    vendorMap: null,
    loadout: null,
    settlement: null,
    buyFair: null,
  });
  const [error, setError] = useState<string | null>(null);
  const [attentionFilter, setAttentionFilter] =
    useState<AttentionFilter>("all");

  const enabledModules = useMemo(() => uniqueModules(event), [event]);
  const hasModule = useCallback(
    (moduleCode: string) => enabledModules.includes(moduleCode),
    [enabledModules],
  );
  const hasVendorHallModule =
    hasModule("vendor-hall-setup") ||
    hasModule("vendor-hall-inventory") ||
    hasModule("event-inventory");
  const hasLoadoutModule =
    hasModule("store-loadout") || hasModule("event-inventory");

  const load = useCallback(async () => {
    const [orders, vendorHall, vendorMap, loadout, settlement, buyFair] =
      await Promise.allSettled([
        hasModule("ordering")
          ? getEventOrderReview(event.id)
          : Promise.resolve(null),
        hasVendorHallModule
          ? getVendorHallSummary(event.id)
          : Promise.resolve(null),
        hasVendorHallModule
          ? getVendorHallFloorMapStatus(event.id)
          : Promise.resolve(null),
        hasLoadoutModule
          ? getStoreLoadoutSummary(event.id)
          : Promise.resolve(null),
        hasModule("event-settlement")
          ? getEventSettlementSummary(event.id)
          : Promise.resolve(null),
        hasModule("vendor-buy-fair")
          ? getEventBuyFairSummary(event.id)
          : Promise.resolve(null),
      ]);
    setState({
      orders: orders.status === "fulfilled" ? orders.value : null,
      vendorHall: vendorHall.status === "fulfilled" ? vendorHall.value : null,
      vendorMap: vendorMap.status === "fulfilled" ? vendorMap.value : null,
      loadout: loadout.status === "fulfilled" ? loadout.value : null,
      settlement: settlement.status === "fulfilled" ? settlement.value : null,
      buyFair: buyFair.status === "fulfilled" ? buyFair.value : null,
    });
    const failures = [
      orders,
      vendorHall,
      vendorMap,
      loadout,
      settlement,
      buyFair,
    ].filter((result) => result.status === "rejected");
    setError(
      failures.length
        ? "Some module summaries could not load yet. Open the related module to configure it."
        : null,
    );
  }, [event.id, hasModule, hasLoadoutModule, hasVendorHallModule]);

  useEffect(() => {
    let active = true;
    const refresh = () =>
      void load().catch((caught: unknown) => {
        if (active) {
          setError(
            caught instanceof Error
              ? caught.message
              : "Event command center could not load",
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

  const eventReadiness = useMemo(() => {
    const scores: number[] = [];
    if (state.vendorHall) {
      scores.push(
        (numericValue(state.vendorHall.completion_percentage) +
          numericValue(state.vendorHall.inventory_completion_percentage)) /
          2,
      );
    }
    if (state.loadout && state.loadout.assignment_total) {
      scores.push(
        (state.loadout.released_from_venue / state.loadout.assignment_total) *
          100,
      );
    }
    if (state.settlement) {
      scores.push(numericValue(state.settlement.readiness_percentage));
    }
    if (!scores.length) return 0;
    return Math.round(
      scores.reduce((total, score) => total + score, 0) / scores.length,
    );
  }, [state]);

  const approvedEventSpend = useMemo(() => {
    if (state.settlement) return state.settlement.approved_spend;
    const liveSpend = Number(state.orders?.approved_spend ?? 0);
    const submittedBuyFairSpend = (state.buyFair?.orders ?? [])
      .filter((order) => order.status !== "vendor_draft")
      .reduce((total, order) => total + Number(order.total_volume), 0);
    return String(liveSpend + submittedBuyFairSpend);
  }, [state.buyFair, state.orders, state.settlement]);

  const attentionItems = useMemo<AttentionItem[]>(() => {
    const items: AttentionItem[] = [];
    if (!event.sub_events.length) {
      items.push({
        title: "No sub-events configured",
        detail: "Add sub-events before assigning modules or attendees.",
        severity: "setup",
        actionLabel: "Open setup",
        onAction: onOpenSetup,
      });
    }
    if (event.sub_events.some((subEvent) => !subEvent.module_codes.length)) {
      items.push({
        title: "Sub-events missing controls",
        detail: "At least one sub-event has no enabled modules.",
        severity: "setup",
        actionLabel: "Open setup",
        onAction: onOpenSetup,
      });
    }
    if (hasModule("ordering") && state.orders?.pending) {
      items.push({
        title: "Orders pending review",
        detail: `${state.orders.pending} order${state.orders.pending === 1 ? "" : "s"} need approval, revision, or rejection.`,
        severity: "warning",
        actionLabel: "Review orders",
        onAction: onOpenOrders,
      });
    }
    if (hasModule("vendor-buy-fair") && state.buyFair?.draft_count) {
      items.push({
        title: "Vendor buy fair drafts",
        detail: `${state.buyFair.draft_count} vendor order${state.buyFair.draft_count === 1 ? "" : "s"} remain in draft and will block final settlement.`,
        severity: "warning",
        actionLabel: "Open buy fair",
        onAction: () => onOpenModule("vendor-buy-fair"),
      });
    }
    if (hasVendorHallModule && state.vendorHall?.exceptions_present) {
      items.push({
        title: "Vendor hall exceptions",
        detail: `${state.vendorHall.exceptions_present} booth${state.vendorHall.exceptions_present === 1 ? "" : "s"} have setup exceptions.`,
        severity: "critical",
        actionLabel: "Open Booth Setup",
        onAction: () => onOpenModule("vendor-hall-setup"),
      });
    }
    if (
      hasVendorHallModule &&
      state.vendorHall &&
      state.vendorHall.vendors_not_submitted.length
    ) {
      items.push({
        title: "Vendors not submitted",
        detail: `${state.vendorHall.vendors_not_submitted.length} vendor${state.vendorHall.vendors_not_submitted.length === 1 ? "" : "s"} have not submitted booth inventory.`,
        severity: "warning",
        actionLabel: "Open Booth Setup",
        onAction: () => onOpenModule("vendor-hall-setup"),
      });
    }
    if (hasLoadoutModule && state.loadout?.exceptions_present) {
      items.push({
        title: "Loadout exceptions",
        detail: `${state.loadout.exceptions_present} store assignment${state.loadout.exceptions_present === 1 ? "" : "s"} have exceptions.`,
        severity: "critical",
        actionLabel: "Open loadout",
        onAction: () => onOpenModule("store-loadout"),
      });
    }
    if (
      hasLoadoutModule &&
      state.loadout &&
      state.loadout.assignment_total > state.loadout.released_from_venue
    ) {
      items.push({
        title: "Stores awaiting release",
        detail: `${state.loadout.assignment_total - state.loadout.released_from_venue} store${state.loadout.assignment_total - state.loadout.released_from_venue === 1 ? "" : "s"} not released from venue.`,
        severity: "warning",
        actionLabel: "Open loadout",
        onAction: () => onOpenModule("store-loadout"),
      });
    }
    if (
      hasModule("event-settlement") &&
      state.settlement?.open_exception_count
    ) {
      items.push({
        title: "Settlement blocked",
        detail: `${state.settlement.open_exception_count} open settlement exception${state.settlement.open_exception_count === 1 ? "" : "s"} must be resolved before closeout.`,
        severity: "critical",
        actionLabel: "Open settlement",
        onAction: () => onOpenModule("event-settlement"),
      });
    }
    if (
      hasModule("event-settlement") &&
      state.settlement?.vendor_hall_closeout_ready === false
    ) {
      items.push({
        title: "Vendor Hall closeout pending",
        detail:
          "All vendor booths must be closed before event settlement can be finalized.",
        severity: "warning",
        actionLabel: "Open Booth Setup",
        onAction: () => onOpenModule("vendor-hall-setup"),
      });
    }
    return items;
  }, [
    event.sub_events,
    hasModule,
    hasLoadoutModule,
    hasVendorHallModule,
    onOpenModule,
    onOpenOrders,
    onOpenSetup,
    state.loadout,
    state.buyFair,
    state.orders,
    state.settlement,
    state.vendorHall,
  ]);

  const filteredAttentionItems = useMemo(
    () =>
      attentionFilter === "all"
        ? attentionItems
        : attentionItems.filter((item) => item.severity === attentionFilter),
    [attentionFilter, attentionItems],
  );

  const attentionCounts = useMemo(
    () => ({
      all: attentionItems.length,
      critical: attentionItems.filter((item) => item.severity === "critical")
        .length,
      warning: attentionItems.filter((item) => item.severity === "warning")
        .length,
      setup: attentionItems.filter((item) => item.severity === "setup").length,
    }),
    [attentionItems],
  );

  function downloadCommandCenterSnapshot() {
    const rows: CsvRow[] = [
      ["section", "field", "value", "detail"],
      ["event", "name", event.name, ""],
      ["event", "status", event.status, ""],
      ["event", "readiness", `${eventReadiness}%`, ""],
      ["event", "sub_events", event.sub_events.length, ""],
      ["event", "attendees", event.memberships.length, ""],
      [
        "event",
        "enabled_modules",
        enabledModules.length,
        enabledModules.join(", "),
      ],
      [
        "orders",
        "approved_spend",
        approvedEventSpend,
        `${state.orders?.pending ?? 0} live pending / ${state.buyFair?.draft_count ?? 0} buy fair drafts`,
      ],
      [
        "vendor_hall",
        "completion",
        state.vendorHall?.completion_percentage ?? "not configured",
        `${state.vendorHall?.exceptions_present ?? 0} exceptions / ${state.vendorHall?.vendors_not_submitted.length ?? 0} vendors not submitted`,
      ],
      [
        "vendor_buy_fair",
        "order_volume",
        state.buyFair?.total_volume ?? "not configured",
        `${state.buyFair?.draft_count ?? 0} drafts / ${state.buyFair?.submitted_count ?? 0} submitted`,
      ],
      [
        "store_loadout",
        "released",
        state.loadout?.released_from_venue ?? "not configured",
        `${state.loadout?.assignment_total ?? 0} assignments / ${state.loadout?.exceptions_present ?? 0} exceptions`,
      ],
      [
        "settlement",
        "status",
        state.settlement?.status ?? "not configured",
        `${state.settlement?.open_exception_count ?? 0} open exceptions / ${state.settlement?.readiness_percentage ?? 0}% readiness`,
      ],
      ...attentionItems.map((item) => [
        "attention",
        item.severity,
        item.title,
        item.detail,
      ]),
      ...event.sub_events.map((subEvent) => [
        "sub_event",
        subEvent.name,
        subEvent.status,
        subEvent.module_codes
          .map((code) => moduleNames[code] ?? code)
          .join(", "),
      ]),
    ];
    downloadCsv(`event-command-center-${event.slug}.csv`, rows);
  }

  return (
    <section className="event-ui space-y-5 rounded-2xl border bg-slate-50 p-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="brand-eyebrow">Event command center</p>
          <h3 className="text-xl font-bold">Operational overview</h3>
          <p className="text-sm text-slate-600">
            Monitor setup, ordering, loadout, and settlement readiness across
            this event before drilling into a selected sub-event.
          </p>
        </div>
        <button
          className="rounded-lg border bg-white px-4 py-2 text-sm font-bold"
          onClick={downloadCommandCenterSnapshot}
          type="button"
        >
          Export snapshot
        </button>
      </div>

      {error ? (
        <p className="rounded-lg bg-amber-50 p-3 text-sm text-amber-900">
          {error}
        </p>
      ) : null}

      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
        <Metric label="Event readiness" value={`${eventReadiness}%`} />
        <Metric label="Sub-events" value={event.sub_events.length} />
        <Metric label="Attendees" value={event.memberships.length} />
        <Metric
          label="Approved spend"
          value={formatCurrency(approvedEventSpend)}
        />
        <Metric
          label="Open exceptions"
          value={state.settlement?.open_exception_count ?? 0}
        />
      </div>

      {state.loadout?.teams.length ? (
        <section className="rounded-2xl border bg-white p-4">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div>
              <p className="brand-eyebrow">Loadout oversight</p>
              <h4 className="font-bold">Team progress</h4>
            </div>
            <strong className="text-amber-700">
              {state.loadout.completion_percentage}% complete
            </strong>
          </div>
          <div className="mt-3 grid gap-3 md:grid-cols-2 xl:grid-cols-3">
            {state.loadout.teams.map((team) => (
              <article
                className="rounded-xl border bg-slate-50 p-3"
                key={team.team_name}
              >
                <div className="flex justify-between gap-2">
                  <strong>{team.team_name}</strong>
                  <span className="text-xs font-bold uppercase text-slate-600">
                    {team.status.replaceAll("_", " ")}
                  </span>
                </div>
                <div className="mt-2 h-2 overflow-hidden rounded-full bg-slate-200">
                  <div
                    className="h-full rounded-full bg-emerald-500"
                    style={{ width: `${team.completion_percentage}%` }}
                  />
                </div>
                <p className="mt-2 text-xs text-slate-600">
                  {team.completion_percentage}% complete · {team.released}/
                  {team.assignment_total} released · {team.reviewed}/
                  {team.assignment_total} reviewed
                </p>
              </article>
            ))}
          </div>
        </section>
      ) : null}

      {state.vendorMap?.booths.length ? (
        <section className="rounded-2xl border bg-white p-4">
          <p className="brand-eyebrow">Vendor hall operations</p>
          <h4 className="font-bold">Live booth progress map</h4>
          <VendorHallLiveMap mapStatus={state.vendorMap} offlineReadOnly />
        </section>
      ) : null}

      <section className="rounded-2xl border bg-white p-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <p className="brand-eyebrow">Attention queue</p>
            <h4 className="font-bold">Admin action items</h4>
          </div>
          <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-bold text-slate-700">
            {filteredAttentionItems.length} shown / {attentionItems.length} open
          </span>
        </div>
        <div className="mt-4 flex flex-wrap gap-2">
          {(
            [
              ["all", "All"],
              ["critical", "Critical"],
              ["warning", "Warnings"],
              ["setup", "Setup"],
            ] as const
          ).map(([filter, label]) => (
            <button
              className={`rounded-full border px-3 py-1 text-xs font-bold ${
                attentionFilter === filter
                  ? "bg-slate-950 text-white"
                  : "bg-white text-slate-700"
              }`}
              key={filter}
              onClick={() => setAttentionFilter(filter)}
              type="button"
            >
              {label} · {attentionCounts[filter]}
            </button>
          ))}
        </div>
        <div className="mt-4 grid gap-3">
          {filteredAttentionItems.map((item) => (
            <AttentionCard item={item} key={`${item.title}-${item.detail}`} />
          ))}
          {!attentionItems.length ? (
            <p className="rounded-xl border border-dashed bg-slate-50 p-4 text-sm text-slate-600">
              No command-center action items are open. Keep monitoring the event
              as vendors, stores, and admins continue working.
            </p>
          ) : null}
          {attentionItems.length && !filteredAttentionItems.length ? (
            <p className="rounded-xl border border-dashed bg-slate-50 p-4 text-sm text-slate-600">
              No action items match this filter.
            </p>
          ) : null}
        </div>
      </section>

      <section className="rounded-2xl border bg-white p-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <p className="brand-eyebrow">Module health</p>
            <h4 className="font-bold">Lifecycle status</h4>
          </div>
          <span className="rounded-full bg-blue-50 px-3 py-1 text-xs font-bold text-blue-800">
            Auto-refreshes every 30 seconds
          </span>
        </div>
        <div className="mt-4 grid gap-3 lg:grid-cols-2">
          <ModuleCard
            detail={
              state.vendorHall
                ? `${state.vendorHall.fully_checked_in}/${state.vendorHall.booth_total} booths · ${state.vendorHall.inventory_items_checked}/${state.vendorHall.inventory_item_total} items`
                : "Enable or configure vendor hall setup"
            }
            enabled={hasVendorHallModule}
            label="Vendor hall"
            onAction={() => onOpenModule("vendor-hall-setup")}
            status={
              state.vendorHall
                ? `${numericValue(state.vendorHall.completion_percentage)}% booths · ${numericValue(state.vendorHall.inventory_completion_percentage)}% inventory`
                : "Not configured"
            }
            tone={state.vendorHall?.exceptions_present ? "danger" : "standard"}
          />
          <ModuleCard
            detail={
              state.orders
                ? `${state.orders.pending} pending · ${state.orders.released} released`
                : "Enable ordering to collect entity demand"
            }
            enabled={hasModule("ordering")}
            label="Order review"
            onAction={onOpenOrders}
            status={
              state.orders
                ? `${state.orders.approved_units} approved units`
                : "Not configured"
            }
            tone={state.orders?.pending ? "warning" : "standard"}
          />
          <ModuleCard
            detail={
              state.buyFair
                ? `${state.buyFair.draft_count} drafts · ${state.buyFair.submitted_count} submitted`
                : "Enable Vendor Buy Fair for event vendor ordering"
            }
            enabled={hasModule("vendor-buy-fair")}
            label="Vendor buy fair"
            onAction={() => onOpenModule("vendor-buy-fair")}
            status={
              state.buyFair
                ? `${state.buyFair.total_units} units · ${formatCurrency(state.buyFair.total_volume)}`
                : "Not configured"
            }
            tone={state.buyFair?.draft_count ? "warning" : "standard"}
          />
          <ModuleCard
            detail={
              state.loadout
                ? `${state.loadout.released_from_venue}/${state.loadout.assignment_total} stores released`
                : "Enable store loadout to assign sold/demo inventory"
            }
            enabled={hasLoadoutModule}
            label="Store loadout"
            onAction={() => onOpenModule("store-loadout")}
            status={
              state.loadout
                ? `${state.loadout.exceptions_present} exception assignments`
                : "Not configured"
            }
            tone={state.loadout?.exceptions_present ? "danger" : "standard"}
          />
          <ModuleCard
            detail={
              state.settlement
                ? `${state.settlement.open_exception_count} open exceptions · ${state.settlement.order_released}/${state.settlement.order_total} orders released${state.settlement.vendor_hall_closeout_ready === false ? " · Vendor Hall pending" : ""}`
                : "Enable settlement to close the event lifecycle"
            }
            enabled={hasModule("event-settlement")}
            label="Settlement"
            onAction={() => onOpenModule("event-settlement")}
            status={
              state.settlement
                ? statusLabel(state.settlement.status)
                : "Not configured"
            }
            tone={
              state.settlement?.open_exception_count ||
              state.settlement?.vendor_hall_closeout_ready === false
                ? "danger"
                : "standard"
            }
          />
        </div>
      </section>

      <section className="overflow-x-auto rounded-2xl border bg-white">
        <div className="min-w-[760px]">
          <div className="grid grid-cols-[1fr_0.8fr_1.4fr_0.6fr_0.6fr] gap-3 bg-slate-50 p-3 text-xs font-bold uppercase text-slate-500">
            <span>Sub-event</span>
            <span>Status</span>
            <span>Enabled controls</span>
            <span>Count</span>
            <span>Open</span>
          </div>
          {event.sub_events.map((subEvent) => (
            <article
              className="grid grid-cols-[1fr_0.8fr_1.4fr_0.6fr_0.6fr] gap-3 border-t p-3 text-sm"
              key={subEvent.id}
            >
              <div>
                <strong className="block">{subEvent.name}</strong>
                <span className="text-slate-500">{subEvent.location}</span>
              </div>
              <span className="capitalize">{subEvent.status}</span>
              <span>
                {subEvent.module_codes.length
                  ? subEvent.module_codes
                      .map((code) => moduleNames[code] ?? code)
                      .join(", ")
                  : "No controls enabled"}
              </span>
              <span>{subEvent.module_codes.length}</span>
              <span>
                <button
                  className="rounded-lg border px-3 py-2 text-xs font-bold"
                  onClick={() =>
                    subEvent.module_codes[0]
                      ? onOpenSubEvent(subEvent.id)
                      : onOpenSetup()
                  }
                  type="button"
                >
                  Open
                </button>
              </span>
            </article>
          ))}
        </div>
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

function AttentionCard({ item }: { item: AttentionItem }) {
  const toneClass =
    item.severity === "critical"
      ? "border-red-200 bg-red-50 text-red-900"
      : item.severity === "warning"
        ? "border-amber-200 bg-amber-50 text-amber-900"
        : "border-blue-200 bg-blue-50 text-blue-900";
  const label =
    item.severity === "critical"
      ? "Critical"
      : item.severity === "warning"
        ? "Needs review"
        : "Setup";
  return (
    <article
      className={`flex flex-wrap items-center justify-between gap-3 rounded-xl border p-4 ${toneClass}`}
    >
      <div>
        <span className="text-xs font-bold uppercase">{label}</span>
        <h5 className="font-bold">{item.title}</h5>
        <p className="text-sm opacity-80">{item.detail}</p>
      </div>
      <button
        className="rounded-lg border bg-white/70 px-3 py-2 text-sm font-bold"
        onClick={item.onAction}
        type="button"
      >
        {item.actionLabel}
      </button>
    </article>
  );
}

function ModuleCard({
  detail,
  enabled,
  label,
  onAction,
  status,
  tone,
}: {
  detail: string;
  enabled: boolean;
  label: string;
  onAction: () => void;
  status: string;
  tone: "danger" | "standard" | "warning";
}) {
  const toneClass =
    tone === "danger"
      ? "border-red-200 bg-red-50 text-red-900"
      : tone === "warning"
        ? "border-amber-200 bg-amber-50 text-amber-900"
        : "border-slate-200 bg-white text-slate-900";
  return (
    <article className={`rounded-xl border p-4 ${toneClass}`}>
      <div className="flex items-center justify-between gap-3">
        <h5 className="font-bold">{label}</h5>
        <span className="rounded-full bg-white/70 px-2 py-1 text-xs font-bold">
          {enabled ? "Enabled" : "Off"}
        </span>
      </div>
      <strong className="mt-3 block capitalize">{status}</strong>
      <p className="mt-1 text-sm opacity-80">{detail}</p>
      <button
        className="mt-4 rounded-lg border bg-white/70 px-3 py-2 text-sm font-bold disabled:opacity-60"
        disabled={!enabled}
        onClick={onAction}
        type="button"
      >
        Open module
      </button>
    </article>
  );
}
