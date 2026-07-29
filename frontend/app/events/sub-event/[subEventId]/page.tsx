"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { EventBrandingProvider } from "@/components/EventBrandingProvider";
import { EventVendorBuyFairWorkspace } from "@/components/EventVendorBuyFairWorkspace";
import { EventOrderingPortal } from "@/components/EventOrderingPortal";
import { EventPresentationDisplay } from "@/components/EventPresentationDisplay";
import { EventVendorBoothLanding } from "@/components/EventVendorBoothLanding";
import { EventVendorHallDirectory } from "@/components/EventVendorHallDirectory";
import { EventVendorBuyFairSummaryPanel } from "@/components/EventVendorBuyFairSummaryPanel";
import { VendorHallOperationsPanel } from "@/components/VendorHallOperationsPanel";
import { EventPresenterConsole } from "@/components/EventPresenterConsole";
import { EventStaffTaskLanding } from "@/components/EventStaffTaskLanding";
import { StoreLoadoutLanding } from "@/components/StoreLoadoutLanding";
import { StoreLoadoutAdministrationPanel } from "@/components/StoreLoadoutAdministrationPanel";
import { EventScopeProvider } from "@/components/EventScopeProvider";
import { ProtectedRoute } from "@/components/ProtectedRoute";
import {
  listMyEvents,
  ManagedEvent,
  ManagedSubEvent,
} from "@/lib/event-admin-api";
import { useAuth } from "@/lib/auth";
import {
  loadoutWorkspaceMode,
  resolveEventLoadoutRole,
} from "@/lib/loadout-role";

export default function EventSubEventPage() {
  const params = useParams<{ subEventId: string }>();
  return (
    <ProtectedRoute loginMode="event">
      <SubEventWorkspace subEventId={params.subEventId} />
    </ProtectedRoute>
  );
}

function SubEventWorkspace({ subEventId }: { subEventId: string }) {
  const { user } = useAuth();
  const router = useRouter();
  const [event, setEvent] = useState<ManagedEvent | null>(null);
  const [subEvent, setSubEvent] = useState<ManagedSubEvent | null>(null);

  useEffect(() => {
    let active = true;
    void listMyEvents()
      .then((events) => {
        if (!active) return;
        const match = events
          .map((item) => ({
            event: item,
            subEvent: item.sub_events.find((sub) => sub.id === subEventId),
          }))
          .find((item) => item.subEvent);
        if (!match) {
          router.replace("/events/entry");
          return;
        }
        setEvent(match.event);
        setSubEvent(match.subEvent ?? null);
      })
      .catch(() => router.replace("/events/entry"));
    return () => {
      active = false;
    };
  }, [router, subEventId]);

  if (!event || !subEvent) {
    return <main className="loading-screen">Loading sub-event…</main>;
  }

  const modules = new Set(subEvent.module_codes);
  const membershipType = event.memberships.find(
    (membership) =>
      membership.email.toLowerCase() === user?.email?.toLowerCase(),
  )?.membership_type;
  const membership = event.memberships.find(
    (item) => item.email.toLowerCase() === user?.email?.toLowerCase(),
  );
  // A registration row can carry a null role while the membership still has
  // an event-wide loadout role. Only a non-null sub-event role should override
  // that fallback, otherwise assigned users appear to have no workspace.
  const loadoutRole = resolveEventLoadoutRole({
    subEventRole: membership?.sub_event_roles[subEventId],
    eventRole: membership?.loadout_role,
    membershipType,
  });
  const isAdmin = Boolean(
    user?.roles.some((role) => ["ADMIN", "SYSTEM_ADMIN"].includes(role)) ||
      ["admin", "system_admin"].includes(membershipType ?? ""),
  );
  const isExecutive = membershipType === "executive";
  const loadoutWorkspace = loadoutWorkspaceMode({
    role: loadoutRole,
    isAdmin,
    isExecutive,
  });
  const adminBuyFairWorkspace = isAdmin && modules.has("vendor-buy-fair");
  const executiveBuyFairWorkspace =
    isExecutive && modules.has("vendor-buy-fair");
  const hasStaffTaskWorkspace =
    modules.has("staff-tasks") ||
    modules.has("store-loadout") ||
    modules.has("event-inventory");
  return (
    <main className="event-ui min-h-screen bg-slate-950 p-4 sm:p-8">
      <EventBrandingProvider>
        <EventScopeProvider eventId={event.id}>
          <div className="mx-auto max-w-6xl">
            <Link
              className="module-home-link mb-5 inline-flex"
              href={`/events/calendar?event_id=${encodeURIComponent(event.id)}`}
            >
              ← Back to event calendar
            </Link>
            <section className="event-glass-pane mb-6 rounded-2xl p-5">
              <p className="brand-eyebrow">Sub-event workspace</p>
              <h1 className="text-3xl font-bold">{subEvent.name}</h1>
              <p className="mt-2 text-slate-300">
                {event.name} · {subEvent.location}
              </p>
              {loadoutRole && modules.has("store-loadout") ? (
                <p className="mt-3 inline-flex rounded-full border border-amber-300/50 bg-amber-300/10 px-3 py-1 text-xs font-bold uppercase tracking-wide text-amber-200">
                  {loadoutRole === "team_lead"
                    ? "Team lead workspace"
                    : loadoutRole === "dockmaster"
                      ? "Dockmaster workspace"
                      : "Loadout overseer workspace"}
                </p>
              ) : null}
            </section>
            {!isAdmin && modules.has("vendor-buy-fair") ? (
              <EventVendorBuyFairWorkspace subEventId={subEvent.id} />
            ) : null}
            {adminBuyFairWorkspace ? (
              <>
                <EventVendorBuyFairSummaryPanel
                  subEventId={subEvent.id}
                  subEventName={subEvent.name}
                />
                <EventVendorHallDirectory eventId={event.id} />
              </>
            ) : null}
            {executiveBuyFairWorkspace ? (
              <EventVendorHallDirectory eventId={event.id} readOnly />
            ) : null}
            {!isAdmin && modules.has("ordering") ? (
              <EventOrderingPortal subEventId={subEvent.id} />
            ) : null}
            {(modules.has("live-display") || modules.has("product-slides")) &&
            !isAdmin ? (
              <EventPresentationDisplay subEventId={subEvent.id} />
            ) : null}
            {(modules.has("live-display") || modules.has("product-slides")) &&
            isAdmin ? (
              <EventPresenterConsole subEvents={[subEvent]} />
            ) : null}
            {hasStaffTaskWorkspace ? (
              <EventStaffTaskLanding
                eventId={event.id}
                subEventId={subEvent.id}
              />
            ) : null}
            {modules.has("vendor-booths") ||
            modules.has("vendor-hall-setup") ||
            modules.has("vendor-hall-inventory") ? (
              <>
                <EventVendorBoothLanding />
                <VendorHallOperationsPanel compact event={event} />
              </>
            ) : null}
            {modules.has("store-loadout") &&
            (loadoutWorkspace === "team_lead" ||
              loadoutWorkspace === "participant") ? (
              <StoreLoadoutLanding />
            ) : null}
            {modules.has("store-loadout") &&
            (loadoutWorkspace === "dockmaster" ||
              loadoutWorkspace === "overseer" ||
              loadoutWorkspace === "admin") ? (
              <StoreLoadoutAdministrationPanel
                event={event}
                mode={
                  loadoutWorkspace === "dockmaster"
                    ? "dockmaster"
                    : loadoutWorkspace === "overseer"
                      ? "overseer"
                      : "admin"
                }
              />
            ) : null}
            {!adminBuyFairWorkspace &&
            !executiveBuyFairWorkspace &&
            (!modules.has("vendor-buy-fair") || isAdmin || isExecutive) &&
            (!modules.has("ordering") || isAdmin || isExecutive) &&
            !modules.has("live-display") &&
            !modules.has("vendor-booths") &&
            !modules.has("vendor-hall-setup") &&
            !modules.has("vendor-hall-inventory") &&
            !hasStaffTaskWorkspace &&
            !modules.has("store-loadout") ? (
              <section className="event-glass-pane rounded-2xl p-5">
                This sub-event has no interactive module assigned to your
                account.
              </section>
            ) : null}
          </div>
        </EventScopeProvider>
      </EventBrandingProvider>
    </main>
  );
}
