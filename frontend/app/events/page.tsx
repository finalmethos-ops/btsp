"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { type ReactNode, useCallback, useEffect, useState } from "react";
import { EventAnnouncementAdministrationPanel } from "@/components/EventAnnouncementAdministrationPanel";
import { EventAttendancePanel } from "@/components/EventAttendancePanel";
import { EventCalendarAdministrationPanel } from "@/components/EventCalendarAdministrationPanel";
import { EventAttendeeManagementPanel } from "@/components/EventAttendeeManagementPanel";
import { EventCommandCenterPanel } from "@/components/EventCommandCenterPanel";
import { EventOrderReviewPanel } from "@/components/EventOrderReviewPanel";
import { EventPollAdministrationPanel } from "@/components/EventPollAdministrationPanel";
import { EventPresenterConsole } from "@/components/EventPresenterConsole";
import { EventProductSlideBuilder } from "@/components/EventProductSlideBuilder";
import { EventSettlementAdministrationPanel } from "@/components/EventSettlementAdministrationPanel";
import { EventFeedbackAdministrationPanel } from "@/components/EventFeedbackAdministrationPanel";
import { EventStaffTaskAdministrationPanel } from "@/components/EventStaffTaskAdministrationPanel";
import { EventVendorBoothAdministrationPanel } from "@/components/EventVendorBoothAdministrationPanel";
import { EventVendorBuyFairSummaryPanel } from "@/components/EventVendorBuyFairSummaryPanel";
import { ProtectedRoute } from "@/components/ProtectedRoute";
import { StoreLoadoutAdministrationPanel } from "@/components/StoreLoadoutAdministrationPanel";
import { SubEventModuleControls } from "@/components/SubEventModuleControls";
import { VendorHallOperationsPanel } from "@/components/VendorHallOperationsPanel";
import { VendorHallFloorPlanUploadPanel } from "@/components/VendorHallFloorPlanUploadPanel";
import { VendorHallSetupPanel } from "@/components/VendorHallSetupPanel";
import { useAuth } from "@/lib/auth";
import {
  listMyEvents,
  ManagedEvent,
  ManagedSubEvent,
} from "@/lib/event-admin-api";
import { hasPermission } from "@/lib/permissions";
import { usesCalendarEventLanding } from "@/lib/event-landing";

const moduleNames: Record<string, string> = {
  "product-slides": "Product slide builder",
  "live-display": "Live display",
  ordering: "Entity product ordering",
  polling: "Live polls and voting",
  "check-in": "Registration and check-in",
  "staff-tasks": "Onsite staff tasks",
  "vendor-booths": "Vendor booth profiles",
  "vendor-hall-setup": "Vendor hall setup",
  "vendor-hall-inventory": "Vendor inventory management",
  "event-inventory": "Event inventory suite",
  "store-loadout": "Store loadout",
  "event-settlement": "Event settlement",
  "vendor-buy-fair": "Vendor buy fair ordering",
};

type AdminTab =
  | "overview"
  | "setup"
  | "tools"
  | "floor-plan"
  | "orders"
  | "closeout";
function shortDate(value: string) {
  return new Date(value).toLocaleDateString([], {
    month: "short",
    day: "numeric",
  });
}

function shortDateTime(value: string) {
  return new Date(value).toLocaleString([], {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

function CollapsibleEventTool({
  label,
  children,
  open,
  onToggle,
}: {
  label: string;
  children: ReactNode;
  open: boolean;
  onToggle: (open: boolean) => void;
}) {
  return (
    <details
      className="event-tool-section rounded-xl border bg-white p-3"
      open={open}
    >
      <summary
        className="cursor-pointer list-none px-2 py-1 font-bold"
        onClick={(event) => {
          event.preventDefault();
          onToggle(!open);
        }}
      >
        {label}
      </summary>
      <div className="mt-3">{children}</div>
    </details>
  );
}

export default function MyEventsPage() {
  return (
    <ProtectedRoute loginMode="event">
      <MyEventsWorkspace />
    </ProtectedRoute>
  );
}

function MyEventsWorkspace() {
  const { user } = useAuth();
  const router = useRouter();
  const isAdmin = Boolean(user && hasPermission(user, "events.manage"));
  const isFranchiseRep = Boolean(user?.roles.includes("FRANCHISE_OPERATOR"));
  const isEventSession = user?.login_context === "event";
  const canReadSettlement = Boolean(
    user && hasPermission(user, "event_settlement.read"),
  );
  const canManageSettlement = Boolean(
    user && hasPermission(user, "event_settlement.manage"),
  );
  const calendarPrimary = usesCalendarEventLanding(user);
  const [events, setEvents] = useState<ManagedEvent[]>([]);
  const [selected, setSelected] = useState<ManagedEvent | null>(null);
  const [selectedSubEventId, setSelectedSubEventId] = useState<string | null>(
    null,
  );
  const [activeAdminTab, setActiveAdminTab] = useState<AdminTab>("overview");
  const [selectedSubEventByEvent, setSelectedSubEventByEvent] = useState<
    Record<string, string>
  >({});
  const [adminTabByEvent, setAdminTabByEvent] = useState<
    Record<string, AdminTab>
  >({});
  const [openToolLabel, setOpenToolLabel] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [showFloorPlanUpload, setShowFloorPlanUpload] = useState(false);

  useEffect(() => {
    if (!calendarPrimary) return;
    const eventId = new URLSearchParams(window.location.search).get("event_id");
    router.replace(
      eventId
        ? `/events/calendar?event_id=${encodeURIComponent(eventId)}`
        : "/events/calendar",
    );
  }, [calendarPrimary, router]);

  useEffect(() => {
    if (
      isEventSession &&
      !new URLSearchParams(window.location.search).get("event_id")
    ) {
      router.replace("/events/entry");
    }
  }, [isEventSession, router]);

  const load = useCallback(
    async (selectedId?: string) => {
      const next = await listMyEvents();
      const active = next.filter(
        (item) => !["completed", "cancelled"].includes(item.status),
      );
      const requestedEventId = isEventSession
        ? new URLSearchParams(window.location.search).get("event_id")
        : null;
      const visible = requestedEventId
        ? active.filter((item) => item.id === requestedEventId)
        : active;
      setEvents(visible);
      setSelected(
        visible.find((item) => item.id === selectedId) ?? visible[0] ?? null,
      );
    },
    [isEventSession],
  );

  useEffect(() => {
    void load().catch((caught: unknown) =>
      setError(
        caught instanceof Error ? caught.message : "Events could not load",
      ),
    );
  }, [load]);

  useEffect(() => {
    if (!selected) {
      setSelectedSubEventId(null);
      setActiveAdminTab("overview");
      return;
    }
    const savedSubEventId = selectedSubEventByEvent[selected.id];
    const savedSubEventStillExists = selected.sub_events.some(
      (item) => item.id === savedSubEventId,
    );
    setSelectedSubEventId(
      savedSubEventStillExists
        ? savedSubEventId
        : (selected.sub_events[0]?.id ?? null),
    );
    setActiveAdminTab(adminTabByEvent[selected.id] ?? "overview");
  }, [adminTabByEvent, selected, selectedSubEventByEvent]);

  const activeSubEvent =
    selected?.sub_events.find((item) => item.id === selectedSubEventId) ?? null;
  const selectedSubEvents: ManagedSubEvent[] = activeSubEvent
    ? [activeSubEvent]
    : [];
  const enabledModules = new Set(activeSubEvent?.module_codes ?? []);
  const currentMembership = selected?.memberships.find(
    (membership) =>
      membership.email.toLowerCase() === user?.email?.toLowerCase(),
  );
  const scopedLoadoutRole = activeSubEvent
    ? Object.prototype.hasOwnProperty.call(
        currentMembership?.sub_event_roles ?? {},
        activeSubEvent.id,
      )
      ? currentMembership?.sub_event_roles[activeSubEvent.id]
      : currentMembership?.loadout_role
    : currentMembership?.loadout_role;
  const effectiveLoadoutRole =
    scopedLoadoutRole ??
    (currentMembership?.membership_type === "dockmaster"
      ? "dockmaster"
      : currentMembership?.membership_type === "overseer"
        ? "overseer"
        : currentMembership?.membership_type === "team_lead"
          ? "team_lead"
          : null);
  const dockmasterEventSession = effectiveLoadoutRole === "dockmaster";
  const selectedEventModuleCount =
    selected?.sub_events.reduce(
      (count, subEvent) => count + subEvent.module_codes.length,
      0,
    ) ?? 0;
  function selectSubEvent(eventId: string, subEventId: string) {
    setSelectedSubEventId(subEventId);
    setOpenToolLabel(null);
    setSelectedSubEventByEvent((current) => ({
      ...current,
      [eventId]: subEventId,
    }));
  }

  function selectAdminTab(eventId: string, tab: AdminTab) {
    setActiveAdminTab(tab);
    setAdminTabByEvent((current) => ({ ...current, [eventId]: tab }));
  }

  function openModule(event: ManagedEvent, moduleCode: string) {
    const targetSubEvent = event.sub_events.find((subEvent) =>
      subEvent.module_codes.includes(moduleCode),
    );
    if (!targetSubEvent) {
      selectAdminTab(event.id, "setup");
      return;
    }
    selectSubEvent(event.id, targetSubEvent.id);
    selectAdminTab(event.id, "tools");
  }

  function openSubEventTools(event: ManagedEvent, subEventId: string) {
    selectSubEvent(event.id, subEventId);
    selectAdminTab(event.id, "tools");
    setOpenToolLabel(null);
  }

  return (
    <main className="event-ui mx-auto max-w-7xl p-4 sm:p-8">
      <p className="brand-eyebrow">Event workspace</p>
      <h1 className="text-3xl font-bold">
        {isEventSession ? (selected?.name ?? "Event Operations") : "My Events"}
      </h1>
      <p className="mt-2 text-slate-600">
        {isEventSession
          ? "Manage this event’s sub-events, attendees, modules, and live operations."
          : "Select an event to manage its sub-events, attendees, modules, and live operations."}
      </p>
      {isEventSession ? (
        <Link
          className="mt-4 inline-flex rounded-xl border px-4 py-3 font-bold"
          href="/events/entry"
        >
          Switch event
        </Link>
      ) : null}
      {isAdmin && !isEventSession ? (
        <Link
          className="mt-4 inline-flex rounded-xl border px-4 py-3 font-bold"
          href="/events/archive"
        >
          View completed &amp; cancelled events
        </Link>
      ) : null}
      {isAdmin && selected ? (
        <button
          className="mt-4 rounded-xl border border-yellow-500 bg-yellow-400 px-5 py-3 font-bold text-slate-950 shadow-lg"
          onClick={() => setShowFloorPlanUpload(true)}
          type="button"
        >
          Upload Vendor Hall Map PDF
        </button>
      ) : null}
      {error ? (
        <p className="mt-5 rounded-xl bg-red-50 p-4 text-red-800">{error}</p>
      ) : null}
      <div
        className={`mt-6 gap-5 ${isEventSession ? "block" : "grid xl:grid-cols-[280px_1fr]"}`}
      >
        <aside className={isEventSession ? "hidden" : "space-y-2"}>
          {events.map((event) => (
            <button
              className={`w-full rounded-xl border p-4 text-left ${selected?.id === event.id ? "selected-object" : "event-glass-pane"}`}
              key={event.id}
              onClick={() => setSelected(event)}
              type="button"
            >
              <strong className="block">{event.name}</strong>
              <span className="text-xs uppercase">{event.status}</span>
              <span className="mt-2 block text-xs text-slate-500">
                {shortDate(event.starts_at)}–{shortDate(event.ends_at)}
              </span>
              <span className="mt-1 block text-xs text-slate-500">
                {event.sub_events.length} sub-event
                {event.sub_events.length === 1 ? "" : "s"} ·{" "}
                {event.memberships.length} attendee
                {event.memberships.length === 1 ? "" : "s"}
              </span>
            </button>
          ))}
          {!events.length ? (
            <p className="rounded-xl border border-dashed p-4 text-sm text-slate-500">
              No pending or active events.
            </p>
          ) : null}
        </aside>
        {selected ? (
          <div className="space-y-5">
            <header className="rounded-2xl bg-slate-950 p-5 text-white">
              <p className="text-sm font-bold uppercase text-blue-300">
                {selected.status}
              </p>
              <h2 className="text-2xl font-bold">{selected.name}</h2>
              <p>
                {selected.venue_name} · {selected.city}, {selected.state_code}
              </p>
              <div className="mt-4 grid gap-3 text-sm sm:grid-cols-3">
                <div className="rounded-xl bg-white/10 p-3">
                  <span className="block text-xs font-bold uppercase text-blue-300">
                    Dates
                  </span>
                  {shortDate(selected.starts_at)}–{shortDate(selected.ends_at)}
                </div>
                <div className="rounded-xl bg-white/10 p-3">
                  <span className="block text-xs font-bold uppercase text-blue-300">
                    Sub-events
                  </span>
                  {selected.sub_events.length}
                </div>
                <div className="rounded-xl bg-white/10 p-3">
                  <span className="block text-xs font-bold uppercase text-blue-300">
                    Enabled controls
                  </span>
                  {selectedEventModuleCount}
                </div>
              </div>
            </header>
            <section className="event-glass-pane rounded-2xl border p-5">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <p className="brand-eyebrow">Schedule</p>
                  <h3 className="text-xl font-bold">Select a sub-event</h3>
                </div>
                {isAdmin ? (
                  <Link
                    className="rounded-lg border px-4 py-2 font-semibold"
                    href="/admin/events"
                  >
                    Edit dates &amp; locations
                  </Link>
                ) : null}
              </div>
              <p className="mt-1 text-sm text-slate-600">
                Choose a sub-event to reveal only the controls enabled for that
                part of the show.
              </p>
              <div className="mt-4 grid gap-3 md:grid-cols-2">
                {selected.sub_events.map((subEvent) => (
                  <article
                    className={`event-sub-event-card rounded-xl border p-4 transition ${activeSubEvent?.id === subEvent.id ? "is-selected" : ""}`}
                    key={subEvent.id}
                  >
                    <button
                      className="w-full text-left"
                      onClick={() => selectSubEvent(selected.id, subEvent.id)}
                      type="button"
                    >
                      <h4 className="font-bold">{subEvent.name}</h4>
                      <p className="text-sm text-slate-600">
                        {subEvent.location} ·{" "}
                        {shortDateTime(subEvent.starts_at)}
                      </p>
                      <p className="mt-1 text-xs font-bold uppercase text-slate-500">
                        {subEvent.status} · {subEvent.module_codes.length}{" "}
                        enabled control
                        {subEvent.module_codes.length === 1 ? "" : "s"}
                      </p>
                      <div className="mt-3 flex flex-wrap gap-2">
                        {subEvent.module_codes
                          .filter((code) => code in moduleNames)
                          .map((code) => (
                            <span
                              className="rounded-full bg-blue-50 px-3 py-1 text-xs font-semibold text-blue-800"
                              key={code}
                            >
                              {moduleNames[code]}
                            </span>
                          ))}
                      </div>
                    </button>
                    <div className="mt-4 flex flex-wrap gap-2 text-left">
                      {isFranchiseRep &&
                      subEvent.module_codes.includes("ordering") ? (
                        <Link
                          className="rounded-lg bg-blue-800 px-3 py-2 text-sm font-bold text-white"
                          href={`/events/order/${subEvent.id}`}
                        >
                          Place orders
                        </Link>
                      ) : null}
                    </div>
                  </article>
                ))}
                {!selected.sub_events.length ? (
                  <p className="rounded-xl border border-dashed p-5 text-slate-500 md:col-span-2">
                    No sub-events exist yet. Use Event Management to add the
                    sessions, fairs, presentations, or show areas that make up
                    this event.
                  </p>
                ) : null}
              </div>
            </section>
            {isAdmin ? (
              <>
                <section className="event-glass-pane rounded-2xl border p-4">
                  <p className="brand-eyebrow">Admin workspace</p>
                  <div className="mt-3 grid gap-2 sm:grid-cols-3 lg:grid-cols-6">
                    {(
                      [
                        ["overview", "Overview"],
                        ["tools", "Sub-event tools"],
                        ["floor-plan", "Floor plan PDF"],
                        ["setup", "Event setup"],
                        ["orders", "Order review"],
                        ...(canReadSettlement
                          ? [["closeout", "Event closeout"]]
                          : []),
                      ] as Array<[AdminTab, string]>
                    ).map(([tab, label]) => (
                      <button
                        className={`event-admin-tab rounded-xl border p-3 text-sm font-bold ${activeAdminTab === tab ? "is-selected" : ""}`}
                        key={tab}
                        onClick={() => selectAdminTab(selected.id, tab)}
                        type="button"
                      >
                        {label}
                      </button>
                    ))}
                  </div>
                </section>
                {activeAdminTab === "overview" ? (
                  <EventCommandCenterPanel
                    event={selected}
                    onOpenModule={(moduleCode) =>
                      openModule(selected, moduleCode)
                    }
                    onOpenOrders={() => selectAdminTab(selected.id, "orders")}
                    onOpenSetup={() => selectAdminTab(selected.id, "setup")}
                    onOpenSubEvent={(subEventId) =>
                      openSubEventTools(selected, subEventId)
                    }
                  />
                ) : null}
                {activeAdminTab === "setup" ? (
                  <section className="event-glass-pane space-y-5 rounded-2xl border p-5">
                    <div>
                      <p className="brand-eyebrow">Event setup</p>
                      <h3 className="text-xl font-bold">
                        Attendees, communications, and calendar
                      </h3>
                      <p className="text-sm text-slate-600">
                        Configure who can attend and what show-wide information
                        they see.
                      </p>
                    </div>
                    <EventAttendeeManagementPanel
                      event={selected}
                      onUpdated={load}
                    />
                    <EventAnnouncementAdministrationPanel event={selected} />
                    <EventCalendarAdministrationPanel event={selected} />
                    {selected.sub_events.some((subEvent) =>
                      subEvent.module_codes.includes("vendor-booths"),
                    ) ? (
                      <CollapsibleEventTool
                        label="Booth profiles"
                        open={openToolLabel === "Booth profiles"}
                        onToggle={(open) =>
                          setOpenToolLabel(open ? "Booth profiles" : null)
                        }
                      >
                        <EventVendorBoothAdministrationPanel event={selected} />
                      </CollapsibleEventTool>
                    ) : null}
                    {selected.sub_events.some((subEvent) =>
                      ["vendor-hall-inventory", "event-inventory"].some(
                        (code) => subEvent.module_codes.includes(code),
                      ),
                    ) ? (
                      <CollapsibleEventTool
                        label="Booth inventory and check-in"
                        open={openToolLabel === "Booth inventory and check-in"}
                        onToggle={(open) =>
                          setOpenToolLabel(
                            open ? "Booth inventory and check-in" : null,
                          )
                        }
                      >
                        <VendorHallOperationsPanel event={selected} />
                      </CollapsibleEventTool>
                    ) : null}
                  </section>
                ) : null}
                {activeAdminTab === "tools" && activeSubEvent ? (
                  <section className="event-glass-pane space-y-5 rounded-2xl border p-5">
                    <div>
                      <p className="brand-eyebrow">Selected sub-event tools</p>
                      <h3 className="text-xl font-bold">
                        {activeSubEvent.name}
                      </h3>
                      <p className="text-sm text-slate-600">
                        Showing only setup and operating tools enabled for this
                        sub-event.
                      </p>
                    </div>
                    <SubEventModuleControls
                      eventId={selected.id}
                      onUpdated={load}
                      subEvents={selectedSubEvents}
                    />
                    {enabledModules.has("staff-tasks") ||
                    enabledModules.has("store-loadout") ||
                    enabledModules.has("event-inventory") ? (
                      <CollapsibleEventTool
                        label="Staff tasks"
                        open={openToolLabel === "Staff tasks"}
                        onToggle={(open) =>
                          setOpenToolLabel(open ? "Staff tasks" : null)
                        }
                      >
                        <EventStaffTaskAdministrationPanel
                          event={selected}
                          subEventId={activeSubEvent.id}
                        />
                      </CollapsibleEventTool>
                    ) : null}
                    {enabledModules.has("vendor-hall-setup") ? (
                      <CollapsibleEventTool
                        label="Vendor hall setup"
                        open={openToolLabel === "Vendor hall setup"}
                        onToggle={(open) =>
                          setOpenToolLabel(open ? "Vendor hall setup" : null)
                        }
                      >
                        <VendorHallSetupPanel event={selected} />
                      </CollapsibleEventTool>
                    ) : null}
                    {enabledModules.has("store-loadout") ||
                    enabledModules.has("event-inventory") ? (
                      <CollapsibleEventTool
                        label="Store loadout inventory"
                        open={openToolLabel === "Store loadout inventory"}
                        onToggle={(open) =>
                          setOpenToolLabel(
                            open ? "Store loadout inventory" : null,
                          )
                        }
                      >
                        <StoreLoadoutAdministrationPanel
                          event={selected}
                          mode={dockmasterEventSession ? "dockmaster" : "admin"}
                        />
                      </CollapsibleEventTool>
                    ) : null}
                    {enabledModules.has("vendor-buy-fair") ? (
                      <CollapsibleEventTool
                        label="Vendor Buy Fair summary"
                        open={openToolLabel === "Vendor Buy Fair summary"}
                        onToggle={(open) =>
                          setOpenToolLabel(
                            open ? "Vendor Buy Fair summary" : null,
                          )
                        }
                      >
                        <EventVendorBuyFairSummaryPanel
                          subEventId={activeSubEvent.id}
                          subEventName={activeSubEvent.name}
                        />
                      </CollapsibleEventTool>
                    ) : null}
                    {enabledModules.has("product-slides") ? (
                      <CollapsibleEventTool
                        label="Product slides"
                        open={openToolLabel === "Product slides"}
                        onToggle={(open) =>
                          setOpenToolLabel(open ? "Product slides" : null)
                        }
                      >
                        <EventProductSlideBuilder
                          subEvents={selectedSubEvents}
                        />
                      </CollapsibleEventTool>
                    ) : null}
                    {enabledModules.has("polling") ? (
                      <CollapsibleEventTool
                        label="Polls and voting"
                        open={openToolLabel === "Polls and voting"}
                        onToggle={(open) =>
                          setOpenToolLabel(open ? "Polls and voting" : null)
                        }
                      >
                        <EventPollAdministrationPanel
                          subEvents={selectedSubEvents}
                        />
                      </CollapsibleEventTool>
                    ) : null}
                    {enabledModules.has("check-in") ? (
                      <CollapsibleEventTool
                        label="Attendance and check-in"
                        open={openToolLabel === "Attendance and check-in"}
                        onToggle={(open) =>
                          setOpenToolLabel(
                            open ? "Attendance and check-in" : null,
                          )
                        }
                      >
                        <EventAttendancePanel subEvents={selectedSubEvents} />
                      </CollapsibleEventTool>
                    ) : null}
                    {enabledModules.has("live-display") ||
                    enabledModules.has("product-slides") ? (
                      <CollapsibleEventTool
                        label="Live presentation controls"
                        open={openToolLabel === "Live presentation controls"}
                        onToggle={(open) =>
                          setOpenToolLabel(
                            open ? "Live presentation controls" : null,
                          )
                        }
                      >
                        <EventPresenterConsole subEvents={selectedSubEvents} />
                      </CollapsibleEventTool>
                    ) : null}
                    {!activeSubEvent.module_codes.length ? (
                      <p className="event-glass-pane rounded-xl border border-dashed p-5 text-slate-400">
                        No controls are enabled for this sub-event yet. Use
                        Available controls above to add only what this sub-event
                        needs.
                      </p>
                    ) : null}
                  </section>
                ) : null}
                {activeAdminTab === "tools" && !activeSubEvent ? (
                  <section className="event-glass-pane rounded-2xl border border-dashed p-5 text-slate-400">
                    Add a sub-event before configuring sub-event tools. Once a
                    sub-event exists, select it above and enable only the tools
                    it needs.
                  </section>
                ) : null}
                {activeAdminTab === "floor-plan" ? (
                  selected.sub_events.some((subEvent) =>
                    subEvent.module_codes.includes("vendor-hall-setup"),
                  ) ? (
                    <VendorHallFloorPlanUploadPanel event={selected} />
                  ) : (
                    <section className="event-glass-pane rounded-2xl border border-dashed p-5 text-slate-400">
                      Enable Vendor hall setup on a sub-event before importing a
                      floor plan.
                    </section>
                  )
                ) : null}
                {activeAdminTab === "closeout" && canReadSettlement ? (
                  <section className="event-glass-pane space-y-5 rounded-2xl border p-5">
                    <div>
                      <p className="brand-eyebrow">Show-wide administration</p>
                      <h3 className="text-xl font-bold">Event closeout</h3>
                      <p className="text-sm text-slate-600">
                        Review settlement readiness and resolve exceptions.
                        Closing a ready event completes every remaining
                        sub-event and moves the show to Archived Events.
                      </p>
                    </div>
                    <EventSettlementAdministrationPanel
                      event={selected}
                      readOnly={!canManageSettlement}
                      onCompleted={() => load()}
                    />
                    <EventFeedbackAdministrationPanel eventId={selected.id} />
                  </section>
                ) : null}
                {activeAdminTab === "orders" ? (
                  <section className="event-glass-pane space-y-5 rounded-2xl border p-5">
                    <div>
                      <p className="brand-eyebrow">Event order review</p>
                      <h3 className="text-xl font-bold">
                        Review submitted event orders
                      </h3>
                      <p className="text-sm text-slate-600">
                        Approve, reject, and release event order demand for this
                        event.
                      </p>
                    </div>
                    <EventOrderReviewPanel eventId={selected.id} />
                  </section>
                ) : null}
              </>
            ) : null}
          </div>
        ) : (
          <p className="rounded-xl border p-5 text-slate-500">
            No events are assigned to your account.
          </p>
        )}
      </div>
      {showFloorPlanUpload && selected ? (
        <div
          aria-label="Upload Vendor Hall Map PDF"
          aria-modal="true"
          className="fixed inset-0 z-[80] overflow-y-auto bg-slate-950/90 p-3 backdrop-blur-sm sm:p-8"
          role="dialog"
        >
          <div className="mx-auto max-w-6xl">
            <div className="mb-3 flex justify-end">
              <button
                className="rounded-xl bg-yellow-400 px-5 py-3 font-bold text-slate-950"
                onClick={() => setShowFloorPlanUpload(false)}
                type="button"
              >
                Close floor-plan upload
              </button>
            </div>
            <VendorHallFloorPlanUploadPanel event={selected} />
          </div>
        </div>
      ) : null}
    </main>
  );
}
