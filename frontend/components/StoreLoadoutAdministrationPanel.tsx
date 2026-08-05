"use client";

import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import { ManagedEvent } from "@/lib/event-admin-api";
import { listManagedStores, StoreRecord } from "@/lib/store-api";
import {
  assignStoreLoadoutTeam,
  autoOrderStoreLoadout,
  completeStoreLoadoutFinalReview,
  configureStoreLoadoutEvent,
  createStoreLoadoutAssignment,
  exportStoreLoadoutPackingListPdf,
  exportStoreLoadoutReport,
  exportStoreLoadoutPackingListsPdf,
  getStoreLoadoutSummary,
  listStoreLoadoutAssignments,
  reassignStoreLoadoutInventory,
  releaseStoreLoadoutAssignment,
  recalculateStoreLoadoutRoutes,
  StoreLoadoutAssignment,
  StoreLoadoutExportReport,
  StoreLoadoutSummary,
  updateStoreLoadoutVehicleStatus,
  estimateStoreLoadoutRoute,
} from "@/lib/store-loadout-api";
import {
  listVendorHallBooths,
  listVendorHallInventory,
  VendorHallInventoryItem,
} from "@/lib/vendor-hall-api";
import { normalizeStateCode } from "@/lib/state-code";

type InventoryOption = VendorHallInventoryItem & {
  booth_number: string;
  booth_name: string;
  vendor_name: string | null;
};

type SelectedItem = {
  itemId: string;
  quantity: number;
};

const vehicleOptions = [
  "Truck 1",
  "Truck 2",
  "Truck 3",
  "Van 1",
  "Van 2",
  "Van 3",
];

const exportReports: Array<{ type: StoreLoadoutExportReport; label: string }> =
  [
    { type: "master", label: "Master report" },
    { type: "packing-lists", label: "Packing lists" },
    { type: "damaged-items", label: "Damaged items" },
    { type: "missing-items", label: "Missing items" },
    { type: "departure-schedule", label: "Departure schedule" },
    { type: "audit-log", label: "Audit log" },
  ];

function toApiDateTime(value: FormDataEntryValue | null) {
  const text = String(value || "");
  return text ? new Date(text).toISOString() : null;
}

function statusLabel(value: string) {
  return value.replaceAll("_", " ");
}

function displayDateTime(value: string | null) {
  if (!value) return "TBD";
  return new Date(value).toLocaleString([], {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

function emailList(value: FormDataEntryValue | null) {
  return String(value || "")
    .split(/[,\n]/)
    .map((item) => item.trim())
    .filter(Boolean);
}

export function StoreLoadoutAdministrationPanel({
  event,
  mode = "admin",
}: {
  event: ManagedEvent;
  mode?: "admin" | "dockmaster" | "overseer";
}) {
  const [summary, setSummary] = useState<StoreLoadoutSummary | null>(null);
  const [assignments, setAssignments] = useState<StoreLoadoutAssignment[]>([]);
  const [inventory, setInventory] = useState<InventoryOption[]>([]);
  const [stores, setStores] = useState<StoreRecord[]>([]);
  const [selectedItems, setSelectedItems] = useState<
    Record<string, SelectedItem>
  >({});
  const [reassignTarget, setReassignTarget] =
    useState<StoreLoadoutAssignment | null>(null);
  const [vendorFilter, setVendorFilter] = useState("all");
  const [vehicleLabels, setVehicleLabels] = useState<string[]>(["Truck 1"]);
  const [selectedStoreNumber, setSelectedStoreNumber] = useState("");
  const [routeEstimate, setRouteEstimate] = useState<{
    distance_miles: number;
    estimated_drive_minutes: number;
    recommended_departure_at: string;
  } | null>(null);
  const [routePending, setRoutePending] = useState(false);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const selectedItemList = useMemo(
    () => Object.values(selectedItems).filter((item) => item.quantity > 0),
    [selectedItems],
  );
  const eventStores = useMemo(
    () =>
      stores.filter(
        (store) =>
          normalizeStateCode(store.state_code) ===
          normalizeStateCode(event.state_code),
      ),
    [event.state_code, stores],
  );
  const eventStaff = useMemo(
    () =>
      event.memberships.filter(
        (member) =>
          ["staff", "admin", "team_lead", "dockmaster", "overseer"].includes(
            member.membership_type,
          ) || Boolean(member.loadout_role),
      ),
    [event.memberships],
  );
  const vendors = useMemo(
    () =>
      Array.from(
        new Map(
          inventory.map((item) => [
            item.vendor_code,
            item.vendor_name ?? item.vendor_code,
          ]),
        ),
      ),
    [inventory],
  );
  const visibleInventory = useMemo(
    () =>
      vendorFilter === "all"
        ? inventory
        : inventory.filter((item) => item.vendor_code === vendorFilter),
    [inventory, vendorFilter],
  );

  const load = useCallback(async () => {
    const [nextSummary, nextAssignments, nextBooths, nextStores] =
      await Promise.all([
        getStoreLoadoutSummary(event.id),
        listStoreLoadoutAssignments(event.id),
        listVendorHallBooths(event.id),
        listManagedStores(true),
      ]);
    setSummary(nextSummary);
    setAssignments(nextAssignments);
    setStores(nextStores);
    const inventoryGroups = await Promise.all(
      nextBooths.map(async (booth) => {
        const items = await listVendorHallInventory(booth.id).catch(
          () => [] as VendorHallInventoryItem[],
        );
        return items.map((item) => ({
          ...item,
          booth_number: booth.booth_number,
          booth_name: booth.booth_name,
          vendor_name: booth.vendor_name,
        }));
      }),
    );
    setInventory(inventoryGroups.flat());
  }, [event.id]);

  useEffect(() => {
    setMessage(null);
    setError(null);
    setSelectedItems({});
    setSelectedStoreNumber("");
    let active = true;
    const refresh = () =>
      void load().catch((caught: unknown) => {
        if (active) {
          setError(
            caught instanceof Error
              ? caught.message
              : "Unable to load store loadout.",
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

  function toggleItem(itemId: string, checked: boolean) {
    setSelectedItems((current) => {
      const next = { ...current };
      if (checked) {
        const item = inventory.find((candidate) => candidate.id === itemId);
        next[itemId] = {
          itemId,
          quantity: Math.min(1, item?.quantity_expected ?? 1),
        };
      } else {
        delete next[itemId];
      }
      return next;
    });
  }

  function setItemQuantity(itemId: string, quantity: number) {
    setSelectedItems((current) => ({
      ...current,
      [itemId]: {
        itemId,
        quantity,
      },
    }));
  }

  async function calculateRoute(storeNumber: string) {
    if (!storeNumber) {
      setRouteEstimate(null);
      setRoutePending(false);
      return;
    }
    setRoutePending(true);
    setRouteEstimate(null);
    try {
      setRouteEstimate(await estimateStoreLoadoutRoute(event.id, storeNumber));
    } catch (caught) {
      setError(
        caught instanceof Error ? caught.message : "Route estimate unavailable",
      );
    } finally {
      setRoutePending(false);
    }
  }

  async function saveLoadoutConfig(formEvent: FormEvent<HTMLFormElement>) {
    formEvent.preventDefault();
    const data = new FormData(formEvent.currentTarget);
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      await configureStoreLoadoutEvent(event.id, {
        status: String(data.get("status")) as "draft" | "open" | "closed",
        opens_at: toApiDateTime(data.get("opens_at")),
        loadout_deadline: toApiDateTime(data.get("loadout_deadline")),
        default_loadout_zone:
          String(data.get("default_loadout_zone") || "") || null,
        venue_departure_notes:
          String(data.get("venue_departure_notes") || "") || null,
        dock_master_email: String(data.get("dock_master_email") || "") || null,
      });
      await load();
      setMessage("Store loadout settings saved.");
    } catch (caught) {
      setError(
        caught instanceof Error
          ? caught.message
          : "Store loadout settings failed",
      );
    } finally {
      setBusy(false);
    }
  }

  async function createAssignment(formEvent: FormEvent<HTMLFormElement>) {
    formEvent.preventDefault();
    const form = formEvent.currentTarget;
    const data = new FormData(form);
    const storeNumber =
      String(data.get("store_number") || "") ||
      reassignTarget?.store_number ||
      "";
    const store = stores.find((item) => item.store_number === storeNumber);
    if (!selectedItemList.length) {
      setError("Select at least one booth item before creating an assignment.");
      return;
    }
    if (!routeEstimate) {
      setError("Select a store and wait for its route estimate before saving.");
      return;
    }
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      const payload = {
        store_number: storeNumber,
        entity_code: store?.entity_code ?? null,
        pickup_priority: Number(data.get("pickup_priority")) || 100,
        loadout_zone: String(data.get("loadout_zone") || "") || null,
        distance_miles: routeEstimate?.distance_miles ?? null,
        estimated_drive_minutes: routeEstimate?.estimated_drive_minutes ?? null,
        recommended_departure_at:
          routeEstimate?.recommended_departure_at ?? null,
        notes: String(data.get("notes") || "") || null,
        vehicle_labels: vehicleLabels,
        items: selectedItemList.map((item) => ({
          vendor_hall_inventory_item_id: item.itemId,
          quantity_assigned: item.quantity,
          vehicle_label: null,
        })),
      };
      if (reassignTarget) {
        await reassignStoreLoadoutInventory(reassignTarget.id, {
          vehicle_labels: payload.vehicle_labels,
          notes: payload.notes,
          items: payload.items,
        });
      } else {
        await createStoreLoadoutAssignment(event.id, payload);
      }
      setSelectedItems({});
      setVehicleLabels(["Truck 1"]);
      setReassignTarget(null);
      setRouteEstimate(null);
      setSelectedStoreNumber("");
      await load();
      form.reset();
      setMessage(
        reassignTarget
          ? "Store inventory reassigned."
          : "Store assignment created.",
      );
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Assignment failed.");
    } finally {
      setBusy(false);
    }
  }

  function beginReassignment(assignment: StoreLoadoutAssignment) {
    setReassignTarget(assignment);
    setSelectedStoreNumber(assignment.store_number);
    void calculateRoute(assignment.store_number);
    const selected: Record<string, SelectedItem> = {};
    assignment.items.forEach((item) => {
      selected[item.vendor_hall_inventory_item_id] = {
        itemId: item.vendor_hall_inventory_item_id,
        quantity: item.quantity_assigned,
      };
    });
    setVehicleLabels(
      assignment.vehicle_labels.length
        ? assignment.vehicle_labels
        : ["Truck 1"],
    );
    setSelectedItems(selected);
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  async function reprintPackingList(assignment: StoreLoadoutAssignment) {
    setBusy(true);
    try {
      await exportStoreLoadoutPackingListPdf(event.id, assignment.id);
      setMessage(
        `Packing list for Store ${assignment.store_number} reprinted.`,
      );
    } catch (caught) {
      setError(
        caught instanceof Error
          ? caught.message
          : "Packing list export failed.",
      );
    } finally {
      setBusy(false);
    }
  }

  async function updateVehicleStatus(
    assignment: StoreLoadoutAssignment,
    vehicle: string,
    status: "loading" | "loaded" | "departed",
  ) {
    setBusy(true);
    setError(null);
    try {
      await updateStoreLoadoutVehicleStatus(assignment.id, vehicle, status);
      await load();
      setMessage(`${assignment.store_number} ${vehicle} marked ${status}.`);
    } catch (caught) {
      setError(
        caught instanceof Error ? caught.message : "Vehicle departure failed",
      );
    } finally {
      setBusy(false);
    }
  }

  async function downloadReport(reportType: StoreLoadoutExportReport) {
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      await exportStoreLoadoutReport(event.id, reportType);
      setMessage("Store loadout export downloaded.");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Export failed.");
    } finally {
      setBusy(false);
    }
  }

  async function optimizeLoadoutOrder() {
    setBusy(true);
    setError(null);
    try {
      await autoOrderStoreLoadout(event.id);
      await load();
      setMessage(
        "Loadout order optimized: farthest stores first; trucks before vans.",
      );
    } catch (caught) {
      setError(
        caught instanceof Error
          ? caught.message
          : "Loadout order optimization failed",
      );
    } finally {
      setBusy(false);
    }
  }

  async function recalculateRoutes() {
    setBusy(true);
    setError(null);
    try {
      const result = await recalculateStoreLoadoutRoutes(event.id);
      if (result.updated) {
        await autoOrderStoreLoadout(event.id);
      }
      await load();
      setMessage(
        result.failed_store_numbers.length
          ? `${result.updated} route(s) updated and load order refreshed. Unable to calculate: ${result.failed_store_numbers.join(", ")}.`
          : `${result.updated} store route(s) updated and load order refreshed.`,
      );
    } catch (caught) {
      setError(
        caught instanceof Error ? caught.message : "Route recalculation failed",
      );
    } finally {
      setBusy(false);
    }
  }

  async function saveTeam(
    assignment: StoreLoadoutAssignment,
    formEvent: FormEvent<HTMLFormElement>,
  ) {
    formEvent.preventDefault();
    const data = new FormData(formEvent.currentTarget);
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      await assignStoreLoadoutTeam(assignment.id, {
        team_name: String(data.get("team_name") || "") || null,
        team_member_emails: emailList(data.get("team_member_emails")),
        team_lead_emails: data.getAll("team_lead_emails").map(String),
        vehicle_labels: assignment.vehicle_labels,
      });
      await load();
      setMessage(`Team assignment saved for store ${assignment.store_number}.`);
    } catch (caught) {
      setError(
        caught instanceof Error ? caught.message : "Team assignment failed",
      );
    } finally {
      setBusy(false);
    }
  }

  async function completeFinalReview(
    assignment: StoreLoadoutAssignment,
    formEvent: FormEvent<HTMLFormElement>,
  ) {
    formEvent.preventDefault();
    const data = new FormData(formEvent.currentTarget);
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      await completeStoreLoadoutFinalReview(assignment.id, {
        notes: String(data.get("review_notes") || "") || null,
      });
      await load();
      setMessage(
        `Final review completed for store ${assignment.store_number}.`,
      );
    } catch (caught) {
      setError(
        caught instanceof Error ? caught.message : "Final review failed",
      );
    } finally {
      setBusy(false);
    }
  }

  const dockmasterMode = mode === "dockmaster";
  const overseerMode = mode === "overseer";

  if (dockmasterMode) {
    return (
      <section className="event-ui rounded-2xl border bg-white p-5">
        <p className="brand-eyebrow">022 · Store Loadout</p>
        <h3 className="text-xl font-bold">Dockmaster controls</h3>
        <p className="mt-1 text-sm text-slate-600">
          Manage the active dock queue, vehicle arrivals, loading, and
          departures.
        </p>
        {message ? (
          <p className="mt-3 rounded-lg bg-green-50 p-3 text-green-800">
            {message}
          </p>
        ) : null}
        {error ? (
          <p className="mt-3 rounded-lg bg-red-50 p-3 text-red-800">{error}</p>
        ) : null}
        <StoreLoadoutLiveDashboard
          assignments={assignments}
          onRefresh={load}
          onError={setError}
          onMessage={setMessage}
        />
      </section>
    );
  }

  return (
    <section className="event-ui rounded-2xl border bg-white p-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="brand-eyebrow">022 · Store Loadout</p>
          <h3 className="text-xl font-bold">
            {overseerMode
              ? "Loadout overseer workspace"
              : "Store loadout assignment"}
          </h3>
          <p className="mt-1 text-sm text-slate-600">
            {overseerMode
              ? "Monitor every team, resolve inventory assignments, and reprint store packing lists."
              : "Assign sold or demo booth inventory to stores, set pickup zones, and monitor mobile checklist progress."}
          </p>
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

      <div className="mt-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-7">
        <Metric label="Assignments" value={summary?.assignment_total ?? 0} />
        <Metric label="Items" value={summary?.item_total ?? 0} />
        <Metric label="In progress" value={summary?.in_progress ?? 0} />
        <Metric label="Exceptions" value={summary?.exceptions_present ?? 0} />
        <Metric
          label="Ready for review"
          value={summary?.ready_for_final_review ?? 0}
        />
        <Metric label="Released" value={summary?.released_from_venue ?? 0} />
        <Metric
          label="Loadout complete"
          value={summary?.completion_percentage ?? 0}
        />
      </div>

      {summary?.teams.length ? (
        <section className="mt-5 rounded-2xl border bg-slate-950 p-4 text-white">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div>
              <p className="brand-eyebrow text-blue-200">Team operations</p>
              <h4 className="font-bold">Current team status</h4>
            </div>
            <span className="text-sm font-bold text-amber-300">
              {summary.completion_percentage}% of total loadout complete
            </span>
          </div>
          <div className="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-3">
            {summary.teams.map((team) => (
              <article
                className="rounded-xl border border-white/15 bg-white/5 p-3"
                key={team.team_name}
              >
                <div className="flex justify-between gap-2">
                  <strong>{team.team_name}</strong>
                  <span className="text-xs font-bold uppercase text-amber-300">
                    {team.status.replaceAll("_", " ")}
                  </span>
                </div>
                <div className="mt-2 h-2 overflow-hidden rounded-full bg-white/15">
                  <div
                    className="h-full rounded-full bg-emerald-400"
                    style={{ width: `${team.completion_percentage}%` }}
                  />
                </div>
                <p className="mt-2 text-xs text-slate-300">
                  {team.completion_percentage}% complete · {team.released}/
                  {team.assignment_total} released · {team.reviewed}/
                  {team.assignment_total} reviewed
                </p>
              </article>
            ))}
          </div>
        </section>
      ) : null}

      <StoreLoadoutLiveDashboard
        assignments={assignments}
        onRefresh={load}
        onError={setError}
        onMessage={setMessage}
        readOnly={overseerMode}
      />

      {!overseerMode ? (
        <form
          className="mt-5 grid gap-3 rounded-2xl border bg-slate-50 p-4 md:grid-cols-2"
          onSubmit={(event) => void saveLoadoutConfig(event)}
        >
          <div className="md:col-span-2">
            <p className="brand-eyebrow">Loadout settings</p>
            <h4 className="font-bold">Open and schedule this loadout</h4>
          </div>
          <label className="grid gap-1 text-sm font-semibold">
            Status
            <select
              className="rounded-lg border p-2"
              name="status"
              defaultValue="open"
            >
              <option value="draft">Draft</option>
              <option value="open">Open</option>
              <option value="closed">Closed</option>
            </select>
          </label>
          <label className="grid gap-1 text-sm font-semibold">
            Default loadout zone
            <input
              className="rounded-lg border p-2"
              name="default_loadout_zone"
              placeholder="Dock A"
            />
          </label>
          <label className="grid gap-1 text-sm font-semibold">
            Opens at
            <input
              className="rounded-lg border p-2"
              name="opens_at"
              type="datetime-local"
            />
          </label>
          <label className="grid gap-1 text-sm font-semibold">
            Deadline
            <input
              className="rounded-lg border p-2"
              name="loadout_deadline"
              type="datetime-local"
            />
          </label>
          <label className="grid gap-1 text-sm font-semibold md:col-span-2">
            Dock master email
            <input
              className="rounded-lg border p-2"
              name="dock_master_email"
              placeholder="dock.master@buddys.com"
              type="email"
            />
          </label>
          <label className="grid gap-1 text-sm font-semibold md:col-span-2">
            Venue departure notes
            <textarea
              className="min-h-20 rounded-lg border p-2"
              name="venue_departure_notes"
              placeholder="Use west dock, keep aisles clear, security must release final trucks."
            />
          </label>
          <button
            className="rounded-xl bg-slate-950 px-4 py-2 font-bold text-white disabled:bg-slate-400 md:col-span-2"
            disabled={busy}
            type="submit"
          >
            Save loadout settings
          </button>
        </form>
      ) : null}

      {!overseerMode || reassignTarget ? (
        <form
          className="mt-5 grid gap-4 rounded-2xl border bg-slate-50 p-4"
          onSubmit={(event) => void createAssignment(event)}
        >
          <div>
            <p className="brand-eyebrow">
              {reassignTarget
                ? "Reassign store inventory"
                : "Create store assignment"}
            </p>
            <h4 className="font-bold">
              {reassignTarget
                ? `Update Store ${reassignTarget.store_number} before final review`
                : "Select a store and booth inventory"}
            </h4>
            <p className="text-sm text-slate-600">
              Selected items appear in the store’s mobile pickup checklist.
            </p>
          </div>
          <div className="grid gap-3 md:grid-cols-3">
            <label className="grid gap-1 text-sm font-semibold">
              Store
              <select
                className="rounded-lg border p-2"
                name="store_number"
                required={!reassignTarget}
                value={selectedStoreNumber}
                onChange={(inputEvent) => {
                  setSelectedStoreNumber(inputEvent.currentTarget.value);
                  setRouteEstimate(null);
                  setError(null);
                }}
              >
                <option value="">Select store</option>
                {eventStores.map((store) => (
                  <option key={store.store_number} value={store.store_number}>
                    {store.store_number} · {store.name}
                  </option>
                ))}
              </select>
              <span className="text-xs font-normal text-slate-500">
                Only active stores in {normalizeStateCode(event.state_code)} are
                available for this event.
              </span>
              <button
                className="rounded-lg bg-yellow-400 px-4 py-2 text-sm font-bold text-slate-950 disabled:cursor-not-allowed disabled:opacity-50"
                disabled={!selectedStoreNumber || routePending}
                onClick={() => void calculateRoute(selectedStoreNumber)}
                type="button"
              >
                {routePending ? "Calculating…" : "Calculate route"}
              </button>
            </label>
            <label className="grid gap-1 text-sm font-semibold">
              Pickup priority
              <input
                className="rounded-lg border p-2"
                defaultValue="100"
                min="1"
                name="pickup_priority"
                type="number"
              />
            </label>
            <label className="grid gap-1 text-sm font-semibold">
              Loadout zone
              <input
                className="rounded-lg border p-2"
                name="loadout_zone"
                placeholder="Dock B"
              />
            </label>
            <label className="grid gap-1 text-sm font-semibold">
              Distance miles
              <input
                className="rounded-lg border p-2"
                readOnly
                value={routeEstimate?.distance_miles ?? ""}
              />
            </label>
            <label className="grid gap-1 text-sm font-semibold">
              Drive minutes
              <input
                className="rounded-lg border p-2"
                readOnly
                value={routeEstimate?.estimated_drive_minutes ?? ""}
              />
            </label>
            <label className="grid gap-1 text-sm font-semibold">
              Recommended departure
              <input
                className="rounded-lg border p-2"
                readOnly
                value={
                  routeEstimate?.recommended_departure_at
                    ? new Date(
                        routeEstimate.recommended_departure_at,
                      ).toLocaleString()
                    : ""
                }
              />
            </label>
            {routePending ? (
              <p className="text-xs font-semibold text-blue-700 md:col-span-3">
                Calculating route and recommended departure…
              </p>
            ) : routeEstimate ? (
              <p className="text-xs text-slate-500 md:col-span-3">
                Route calculated from the event address. Recommended departure
                targets arrival by 6:00 PM.
              </p>
            ) : (
              <p className="text-xs font-semibold text-amber-700 md:col-span-3">
                A current route estimate is required before this assignment can
                be saved.
              </p>
            )}
          </div>
          <fieldset className="grid gap-2 rounded-xl border bg-white p-3">
            <legend className="px-1 text-sm font-bold">
              Expected vehicles
            </legend>
            <span className="text-xs font-normal text-slate-500">
              Select the vehicles expected from this store before the event.
            </span>
            <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
              {vehicleOptions.map((vehicle) => (
                <label
                  className="event-selectable flex items-center gap-2 rounded-lg border p-2 text-sm"
                  key={vehicle}
                >
                  <input
                    checked={vehicleLabels.includes(vehicle)}
                    onChange={(inputEvent) => {
                      const checked = inputEvent.currentTarget.checked;
                      setVehicleLabels((current) =>
                        checked
                          ? current.includes(vehicle)
                            ? current
                            : [...current, vehicle]
                          : current.filter((item) => item !== vehicle),
                      );
                    }}
                    type="checkbox"
                  />
                  {vehicle}
                </label>
              ))}
            </div>
          </fieldset>
          <label className="grid gap-1 text-sm font-semibold">
            Assignment notes
            <textarea className="min-h-20 rounded-lg border p-2" name="notes" />
          </label>

          <div className="overflow-hidden rounded-xl border bg-white">
            <div className="flex flex-wrap items-center justify-between gap-2 border-b bg-slate-50 p-3">
              <strong>Inventory to assign</strong>
              <select
                className="rounded-lg border bg-white p-2 text-sm"
                onChange={(inputEvent) =>
                  setVendorFilter(inputEvent.currentTarget.value)
                }
                value={vendorFilter}
              >
                <option value="all">All vendors</option>
                {vendors.map(([code, name]) => (
                  <option key={code} value={code}>
                    {name}
                  </option>
                ))}
              </select>
            </div>
            <div className="grid grid-cols-[44px_1.1fr_0.7fr_0.6fr_90px] gap-3 bg-slate-50 p-3 text-xs font-bold uppercase text-slate-500">
              <span />
              <span>Item</span>
              <span>Booth</span>
              <span>Available</span>
              <span>Assign</span>
            </div>
            {visibleInventory.map((item) => {
              const selected = selectedItems[item.id];
              return (
                <article
                  className={`selection-pane grid grid-cols-[44px_1.1fr_0.7fr_0.6fr_90px] gap-3 border-t p-3 text-sm ${selected ? "is-selected" : ""}`}
                  key={item.id}
                >
                  <input
                    aria-label={`Select ${item.item_name}`}
                    checked={Boolean(selected)}
                    onChange={(inputEvent) =>
                      toggleItem(item.id, inputEvent.currentTarget.checked)
                    }
                    type="checkbox"
                  />
                  <div>
                    <strong className="block">{item.item_name}</strong>
                    <span className="text-slate-500">
                      Model {item.model_number ?? "N/A"} · {item.condition}
                    </span>
                  </div>
                  <span>
                    {item.booth_number || "TBD"} ·{" "}
                    {item.vendor_name ?? item.vendor_code}
                  </span>
                  <span>{item.quantity_expected}</span>
                  <div className="grid gap-1">
                    <input
                      className="rounded-lg border p-2"
                      disabled={!selected}
                      min="1"
                      max={item.quantity_expected}
                      onChange={(inputEvent) =>
                        setItemQuantity(
                          item.id,
                          Number(inputEvent.currentTarget.value),
                        )
                      }
                      type="number"
                      value={selected?.quantity ?? 1}
                    />
                  </div>
                </article>
              );
            })}
            {!inventory.length ? (
              <p className="border-t p-5 text-sm text-slate-500">
                No matching vendor hall inventory is available yet. Sync vendor
                booths and have vendors submit inventory before creating store
                loadouts.
              </p>
            ) : null}
          </div>

          <button
            className="rounded-xl bg-blue-800 px-4 py-2 font-bold text-white disabled:bg-slate-400"
            disabled={
              busy || routePending || !routeEstimate || !selectedItemList.length
            }
            type="submit"
          >
            {reassignTarget
              ? "Save inventory reassignment"
              : "Create store assignment"}
          </button>
          {reassignTarget ? (
            <button
              className="rounded-xl border px-4 py-2 font-bold"
              onClick={() => {
                setReassignTarget(null);
                setSelectedItems({});
                setRouteEstimate(null);
              }}
              type="button"
            >
              Cancel reassignment
            </button>
          ) : null}
        </form>
      ) : null}

      <section className="mt-5 rounded-2xl border bg-white p-4">
        <p className="brand-eyebrow">Reports / Exports</p>
        <h4 className="font-bold">Store loadout exports</h4>
        <p className="mt-1 text-sm text-slate-600">
          Download packing lists, exception reports, departure schedules, and
          audit activity for final reconciliation.
        </p>
        <div className="mt-4 flex flex-wrap gap-2">
          {!overseerMode ? (
            <button
              className="rounded-lg bg-amber-400 px-3 py-2 text-sm font-bold text-slate-950 disabled:bg-slate-300"
              disabled={busy || !assignments.length}
              onClick={() => void optimizeLoadoutOrder()}
              type="button"
            >
              Auto-order teams by distance
            </button>
          ) : null}
          {!overseerMode ? (
            <span className="self-center text-xs text-slate-500">
              Farthest stores first within each team; unassigned stores last.
            </span>
          ) : null}
          {!overseerMode ? (
            <button
              className="rounded-lg border border-amber-300 bg-amber-400 px-3 py-2 text-sm font-bold text-slate-950 shadow-sm disabled:bg-slate-300 disabled:text-slate-600"
              disabled={busy || !assignments.length}
              onClick={() => void recalculateRoutes()}
              type="button"
            >
              Recalculate routes
            </button>
          ) : null}
          {!overseerMode ? (
            <span className="self-center text-xs text-slate-500">
              Recalculating also refreshes team priority order.
            </span>
          ) : null}
          <button
            className="rounded-lg bg-blue-800 px-3 py-2 text-sm font-bold text-white disabled:bg-slate-400"
            disabled={busy}
            onClick={() =>
              void (async () => {
                setBusy(true);
                try {
                  await exportStoreLoadoutPackingListsPdf(event.id);
                  setMessage("Batch packing-list PDF downloaded.");
                } catch (caught) {
                  setError(
                    caught instanceof Error ? caught.message : "Export failed.",
                  );
                } finally {
                  setBusy(false);
                }
              })()
            }
            type="button"
          >
            Print all packing lists (PDF)
          </button>
          {!overseerMode
            ? exportReports.map((report) => (
                <button
                  className="rounded-lg border px-3 py-2 text-sm font-bold disabled:bg-slate-100"
                  disabled={busy}
                  key={report.type}
                  onClick={() => void downloadReport(report.type)}
                  type="button"
                >
                  {report.label}
                </button>
              ))
            : null}
        </div>
      </section>

      <section className="store-loadout-assignment-table mt-5 overflow-x-auto rounded-xl border bg-white">
        <div className="store-loadout-assignment-table-body min-w-[1120px]">
          <div className="store-loadout-assignment-header grid grid-cols-[0.8fr_0.8fr_0.7fr_0.7fr_0.8fr_0.6fr_0.7fr] gap-3 bg-slate-50 p-3 text-xs font-bold uppercase text-slate-500">
            <span>Store</span>
            <span>Status</span>
            <span>Zone</span>
            <span>Departure</span>
            <span>Team</span>
            <span>Items</span>
            <span>Release</span>
          </div>
          {assignments.map((assignment) => (
            <article
              className="store-loadout-assignment-row grid grid-cols-[0.8fr_0.8fr_0.7fr_0.7fr_0.8fr_0.6fr_0.7fr] gap-3 border-t p-3 text-sm"
              key={assignment.id}
            >
              <div data-label="Store">
                <strong className="block">
                  Store {assignment.store_number}
                </strong>
                <span className="text-slate-500">{assignment.store_name}</span>
                <span className="mt-1 block text-xs font-semibold text-blue-700">
                  Vehicles: {assignment.vehicle_labels.join(", ") || "Truck 1"}
                </span>
              </div>
              <span className="capitalize" data-label="Status">
                {statusLabel(assignment.status)}
              </span>
              <span data-label="Zone">{assignment.loadout_zone ?? "TBD"}</span>
              <span data-label="Departure">
                {displayDateTime(assignment.recommended_departure_at)}
              </span>
              <div data-label="Team">
                <strong className="block">
                  {assignment.team_name ?? "Unassigned"}
                </strong>
                <span className="text-xs text-slate-500">
                  Leads: {assignment.team_lead_emails.join(", ") || "TBD"}
                </span>
                {assignment.final_review_requested_at ? (
                  <span className="mt-1 block text-xs text-blue-800">
                    Review requested{" "}
                    {displayDateTime(assignment.final_review_requested_at)}
                  </span>
                ) : null}
                {assignment.final_review_completed_at ? (
                  <span className="mt-1 block text-xs text-green-800">
                    Reviewed{" "}
                    {displayDateTime(assignment.final_review_completed_at)}
                  </span>
                ) : null}
              </div>
              <span data-label="Items">
                {assignment.item_count}
                {assignment.exception_count
                  ? ` · ${assignment.exception_count} exception`
                  : ""}
              </span>
              <span data-label="Release">
                <div className="grid gap-1">
                  {!overseerMode && assignment.status === "signed_complete"
                    ? assignment.vehicle_labels.map((vehicle) => (
                        <div className="grid gap-1" key={vehicle}>
                          <span className="text-xs font-semibold">
                            {vehicle}:{" "}
                            {assignment.vehicle_statuses[vehicle] ?? "expected"}
                          </span>
                          {(assignment.vehicle_statuses[vehicle] ??
                            "expected") !== "departed" ? (
                            <button
                              className="rounded-lg bg-green-700 px-2 py-1 text-xs font-bold text-white disabled:bg-slate-400"
                              disabled={busy}
                              onClick={() =>
                                void updateVehicleStatus(
                                  assignment,
                                  vehicle,
                                  (assignment.vehicle_statuses[vehicle] ??
                                    "expected") === "expected"
                                    ? "loading"
                                    : (assignment.vehicle_statuses[vehicle] ??
                                          "expected") === "loading"
                                      ? "loaded"
                                      : "departed",
                                )
                              }
                              type="button"
                            >
                              {(assignment.vehicle_statuses[vehicle] ??
                                "expected") === "expected"
                                ? "Start loading"
                                : (assignment.vehicle_statuses[vehicle] ??
                                      "expected") === "loading"
                                  ? "Mark loaded"
                                  : "Mark departed"}
                            </button>
                          ) : null}
                        </div>
                      ))
                    : null}
                  <button
                    className="rounded-lg border px-2 py-1 text-xs font-bold"
                    disabled={busy}
                    onClick={() => void reprintPackingList(assignment)}
                    type="button"
                  >
                    Reprint list
                  </button>
                  {!assignment.final_review_completed_at &&
                  !assignment.signed_at &&
                  !assignment.released_at ? (
                    <button
                      className="rounded-lg border border-amber-500 px-2 py-1 text-xs font-bold text-amber-800"
                      disabled={busy}
                      onClick={() => beginReassignment(assignment)}
                      type="button"
                    >
                      Reassign inventory
                    </button>
                  ) : null}
                  {assignment.released_at
                    ? `Released ${displayDateTime(assignment.released_at)}`
                    : assignment.status === "signed_complete"
                      ? "Mark each vehicle departed"
                      : "Awaiting signature"}
                </div>
              </span>
            </article>
          ))}
        </div>
        {!assignments.length ? (
          <p className="border-t p-5 text-sm text-slate-500">
            No store assignments have been created yet.
          </p>
        ) : null}
      </section>

      {!overseerMode ? (
        <section className="mt-5 rounded-2xl border bg-white p-4">
          <p className="brand-eyebrow">Final review queue</p>
          <h4 className="font-bold">Complete event staff review</h4>
          <p className="mt-1 text-sm text-slate-600">
            When store staff marks a list ready, the assigned event staff lead
            can complete review here before the store signs the packing list.
          </p>
          <div className="mt-4 grid gap-3 lg:grid-cols-2">
            {assignments
              .filter(
                (assignment) =>
                  assignment.status === "ready_for_final_review" &&
                  !assignment.final_review_completed_at,
              )
              .map((assignment) => (
                <form
                  className="grid gap-3 rounded-xl border bg-slate-50 p-4"
                  key={assignment.id}
                  onSubmit={(event) =>
                    void completeFinalReview(assignment, event)
                  }
                >
                  <div>
                    <strong>Store {assignment.store_number}</strong>
                    <p className="text-xs text-slate-500">
                      {assignment.team_name ?? "No team"} · leads{" "}
                      {assignment.team_lead_emails.join(", ") || "TBD"}
                    </p>
                    <p className="mt-1 text-xs text-blue-800">
                      Ready since{" "}
                      {displayDateTime(assignment.final_review_requested_at)}
                    </p>
                  </div>
                  <label className="grid gap-1 text-sm font-semibold">
                    Review notes
                    <textarea
                      className="min-h-16 rounded-lg border p-2"
                      name="review_notes"
                      placeholder="Confirmed quantities, exceptions reviewed, ready for store signature."
                    />
                  </label>
                  <button
                    className="rounded-xl bg-green-700 px-4 py-2 font-bold text-white disabled:bg-slate-400"
                    disabled={busy}
                    type="submit"
                  >
                    Complete final review
                  </button>
                </form>
              ))}
          </div>
          {!assignments.some(
            (assignment) =>
              assignment.status === "ready_for_final_review" &&
              !assignment.final_review_completed_at,
          ) ? (
            <p className="mt-4 rounded-xl border border-dashed bg-slate-50 p-5 text-sm text-slate-500">
              No store loadouts are waiting on event staff final review.
            </p>
          ) : null}
        </section>
      ) : null}

      {!overseerMode ? (
        <section className="mt-5 rounded-2xl border bg-white p-4">
          <p className="brand-eyebrow">Loadout teams</p>
          <h4 className="font-bold">
            Assign store staff and event staff leads
          </h4>
          <p className="mt-1 text-sm text-slate-600">
            Store teams perform the mobile checklist. Assigned event staff leads
            handle final review once a store marks its list ready.
          </p>
          <div className="mt-4 grid gap-3 lg:grid-cols-2">
            {assignments.map((assignment) => (
              <form
                className="grid gap-3 rounded-xl border bg-slate-50 p-4"
                key={assignment.id}
                onSubmit={(event) => void saveTeam(assignment, event)}
              >
                <div>
                  <strong>Store {assignment.store_number}</strong>
                  <p className="text-xs text-slate-500">
                    {assignment.status.replaceAll("_", " ")}
                    {assignment.final_review_requested_at
                      ? ` · ready for final review`
                      : ""}
                  </p>
                </div>
                <label className="grid gap-1 text-sm font-semibold">
                  Team name
                  <select
                    className="rounded-lg border p-2"
                    defaultValue={assignment.team_name ?? ""}
                    name="team_name"
                  >
                    <option value="">Select team</option>
                    {[
                      ["Team Yellow", "yellow"],
                      ["Team Blue", "blue"],
                      ["Team Black", "black"],
                      ["Team Green", "green"],
                    ].map(([label, value]) => (
                      <option key={value} value={label}>
                        {label}
                      </option>
                    ))}
                  </select>
                </label>
                <label className="grid gap-1 text-sm font-semibold">
                  Store team roster (optional)
                  <textarea
                    className="min-h-16 rounded-lg border p-2"
                    defaultValue={assignment.team_member_emails.join(", ")}
                    name="team_member_emails"
                    placeholder="Store manager, driver, assistant"
                  />
                </label>
                <label className="grid gap-1 text-sm font-semibold">
                  Event staff lead emails
                  <select
                    className="min-h-16 rounded-lg border p-2"
                    defaultValue={assignment.team_lead_emails}
                    multiple
                    name="team_lead_emails"
                  >
                    {eventStaff.map((member) => (
                      <option key={member.id} value={member.email}>
                        {member.display_name} · {member.email}
                      </option>
                    ))}
                  </select>
                </label>
                <button
                  className="rounded-xl bg-slate-950 px-4 py-2 font-bold text-white disabled:bg-slate-400"
                  disabled={busy}
                  type="submit"
                >
                  Save team
                </button>
              </form>
            ))}
          </div>
        </section>
      ) : null}
    </section>
  );
}

function Metric({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-xl border bg-white p-3">
      <span className="text-xs font-bold uppercase text-slate-500">
        {label}
      </span>
      <strong className="mt-1 block text-2xl">{value}</strong>
    </div>
  );
}

function StoreLoadoutLiveDashboard({
  assignments,
  onRefresh,
  onError,
  onMessage,
  readOnly = false,
}: {
  assignments: StoreLoadoutAssignment[];
  onRefresh: () => Promise<void>;
  onError: (message: string | null) => void;
  onMessage: (message: string | null) => void;
  readOnly?: boolean;
}) {
  const [dockVehicleLabel, setDockVehicleLabel] = useState("");
  const [vehicleBusy, setVehicleBusy] = useState(false);
  const zoneGroups = useMemo(() => {
    const groups = new Map<string, StoreLoadoutAssignment[]>();
    assignments.forEach((assignment) => {
      const zone = assignment.loadout_zone || "Unassigned zone";
      groups.set(zone, [...(groups.get(zone) ?? []), assignment]);
    });
    return [...groups.entries()].sort(([a], [b]) => a.localeCompare(b));
  }, [assignments]);

  const boothSummary = useMemo(() => {
    const booths = new Map<
      string,
      {
        assigned: number;
        found: number;
        exceptions: number;
        released: number;
      }
    >();
    assignments.forEach((assignment) => {
      const allVehiclesDeparted =
        assignment.vehicle_labels.length > 0 &&
        assignment.vehicle_labels.every(
          (vehicle) =>
            (assignment.vehicle_statuses[vehicle] ?? "expected") === "departed",
        );
      assignment.items.forEach((item) => {
        const key = item.booth_number || "TBD";
        const current = booths.get(key) ?? {
          assigned: 0,
          found: 0,
          exceptions: 0,
          released: 0,
        };
        current.assigned += item.quantity_assigned;
        current.found += item.quantity_found;
        if (
          ["damaged", "missing", "quantity_mismatch", "substituted"].includes(
            item.status,
          )
        ) {
          current.exceptions += 1;
        }
        if (
          assignment.status === "released_from_venue" ||
          allVehiclesDeparted
        ) {
          current.released += item.quantity_assigned;
        }
        booths.set(key, current);
      });
    });
    return [...booths.entries()].sort(([a], [b]) => a.localeCompare(b));
  }, [assignments]);

  const unsigned = assignments.filter((assignment) =>
    ["ready_for_final_review", "exceptions_present"].includes(
      assignment.status,
    ),
  );
  const exceptionAssignments = assignments.filter(
    (assignment) => assignment.exception_count > 0,
  );
  const readyForDeparture = assignments.filter(
    (assignment) =>
      assignment.status === "signed_complete" ||
      Boolean(assignment.final_review_completed_at),
  );
  const dockQueue = [...assignments]
    .filter((assignment) => assignment.status !== "released_from_venue")
    .sort((a, b) => a.pickup_priority - b.pickup_priority);
  const activeDockAssignment =
    dockQueue.find(
      (assignment) =>
        assignment.status === "signed_complete" ||
        Boolean(assignment.final_review_completed_at),
    ) ??
    dockQueue[0] ??
    null;
  const visibleDockQueue = activeDockAssignment
    ? [
        activeDockAssignment,
        ...dockQueue.filter(
          (assignment) => assignment.id !== activeDockAssignment.id,
        ),
      ].slice(0, 3)
    : [];

  async function addDockVehicle(assignment: StoreLoadoutAssignment) {
    const label = dockVehicleLabel.trim();
    if (!label) return;
    if (assignment.vehicle_labels.includes(label)) {
      onError(
        `${label} is already listed for Store ${assignment.store_number}.`,
      );
      return;
    }
    setVehicleBusy(true);
    onError(null);
    try {
      await assignStoreLoadoutTeam(assignment.id, {
        team_name: assignment.team_name,
        team_member_emails: assignment.team_member_emails,
        team_lead_emails: assignment.team_lead_emails,
        vehicle_labels: [...assignment.vehicle_labels, label],
      });
      setDockVehicleLabel("");
      await onRefresh();
      onMessage(`${label} added for Store ${assignment.store_number}.`);
    } catch (caught) {
      onError(
        caught instanceof Error ? caught.message : "Unable to add the vehicle.",
      );
    } finally {
      setVehicleBusy(false);
    }
  }

  async function advanceDockVehicle(
    assignment: StoreLoadoutAssignment,
    vehicle: string,
  ) {
    const current = assignment.vehicle_statuses[vehicle] ?? "expected";
    const next =
      current === "expected"
        ? "loading"
        : current === "loading"
          ? "loaded"
          : current === "loaded"
            ? "departed"
            : null;
    if (!next) return;
    setVehicleBusy(true);
    onError(null);
    try {
      await updateStoreLoadoutVehicleStatus(assignment.id, vehicle, next);
      await onRefresh();
      onMessage(
        `Store ${assignment.store_number} ${vehicle} marked ${
          next === "departed" ? "departed" : next
        }.`,
      );
    } catch (caught) {
      onError(
        caught instanceof Error
          ? caught.message
          : "Unable to update the vehicle status.",
      );
    } finally {
      setVehicleBusy(false);
    }
  }

  async function finalizeDockRelease(assignment: StoreLoadoutAssignment) {
    setVehicleBusy(true);
    onError(null);
    try {
      await releaseStoreLoadoutAssignment(assignment.id);
      await onRefresh();
      onMessage(`Store ${assignment.store_number} released from the venue.`);
    } catch (caught) {
      onError(
        caught instanceof Error
          ? caught.message
          : "Unable to complete the store release.",
      );
    } finally {
      setVehicleBusy(false);
    }
  }

  return (
    <section className="mt-5 rounded-2xl border bg-slate-950 p-4 text-white">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="brand-eyebrow text-blue-200">Live loadout dashboard</p>
          <h4 className="text-xl font-bold">
            Store progress and booth clearance
          </h4>
          <p className="mt-1 text-sm text-slate-300">
            Auto-refreshes every 30 seconds while this event workspace is open.
          </p>
        </div>
        <div className="loadout-live-kpis grid grid-cols-3 gap-2 text-center text-xs">
          <LiveQueue label="Unsigned" value={unsigned.length} tone="yellow" />
          <LiveQueue
            label="Exceptions"
            value={exceptionAssignments.length}
            tone="red"
          />
          <LiveQueue
            label="Ready to depart"
            value={readyForDeparture.length}
            tone="green"
          />
        </div>
      </div>

      <section className="mt-4 rounded-2xl border border-amber-300/30 bg-amber-300/10 p-4">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div>
            <p className="brand-eyebrow text-amber-200">Dock queue</p>
            <h5 className="font-bold">Vehicle call-up order</h5>
          </div>
          <span className="text-xs font-bold text-amber-200">
            One store completes all vehicles before the next store is called
          </span>
        </div>
        {activeDockAssignment ? (
          <div className="mt-3 grid gap-2 md:grid-cols-3">
            {visibleDockQueue.map((assignment, index) => (
              <article
                className={`rounded-xl border p-3 ${
                  assignment.id === activeDockAssignment.id
                    ? "border-amber-300 bg-amber-300/20"
                    : "border-white/10 bg-white/5"
                }`}
                key={assignment.id}
              >
                <div className="flex justify-between gap-2 text-sm">
                  <strong>
                    {index === 0 ? "Now / next" : `Queue ${index + 1}`} · Store{" "}
                    {assignment.store_number}
                  </strong>
                  <span className="text-xs capitalize">
                    {statusLabel(assignment.status)}
                  </span>
                </div>
                <p className="mt-2 text-xs text-slate-300">
                  Vehicles:{" "}
                  {assignment.vehicle_labels
                    .map(
                      (vehicle) =>
                        `${vehicle} (${assignment.vehicle_statuses[vehicle] ?? "expected"})`,
                    )
                    .join(", ") || "Truck 1 (expected)"}
                </p>
                {!readOnly &&
                assignment.id === activeDockAssignment.id &&
                (assignment.status === "signed_complete" ||
                  Boolean(assignment.final_review_completed_at)) ? (
                  <div className="mt-3 grid gap-2">
                    {assignment.vehicle_labels.map((vehicle) => {
                      const vehicleStatus =
                        assignment.vehicle_statuses[vehicle] ?? "expected";
                      const action =
                        vehicleStatus === "expected"
                          ? "Start loading"
                          : vehicleStatus === "loading"
                            ? "Mark loaded"
                            : vehicleStatus === "loaded"
                              ? "Mark departed"
                              : null;
                      return (
                        <div
                          className="loadout-dock-vehicle-row flex flex-wrap items-center justify-between gap-2 rounded-lg border border-white/10 bg-slate-950/60 px-2 py-1.5 text-xs"
                          key={vehicle}
                        >
                          <span>
                            <strong>{vehicle}</strong> · {vehicleStatus}
                          </span>
                          {action ? (
                            <button
                              className="rounded-lg bg-amber-300 px-2.5 py-1.5 font-bold text-slate-950 disabled:opacity-50"
                              disabled={vehicleBusy}
                              onClick={() =>
                                void advanceDockVehicle(assignment, vehicle)
                              }
                              type="button"
                            >
                              {action}
                            </button>
                          ) : (
                            <span className="font-bold text-green-300">
                              Departed
                            </span>
                          )}
                        </div>
                      );
                    })}
                    {assignment.vehicle_labels.length > 0 &&
                    assignment.vehicle_labels.every(
                      (vehicle) =>
                        (assignment.vehicle_statuses[vehicle] ?? "expected") ===
                        "departed",
                    ) ? (
                      <button
                        className="rounded-lg bg-green-400 px-2.5 py-1.5 text-xs font-bold text-green-950 disabled:opacity-50"
                        disabled={vehicleBusy}
                        onClick={() => void finalizeDockRelease(assignment)}
                        type="button"
                      >
                        Finalize store departure
                      </button>
                    ) : null}
                  </div>
                ) : null}
                <p className="mt-1 text-xs text-slate-400">
                  Priority {assignment.pickup_priority} ·{" "}
                  {assignment.item_count} assigned items
                </p>
              </article>
            ))}
          </div>
        ) : (
          <p className="mt-3 text-sm text-slate-300">
            No stores are currently queued at the dock.
          </p>
        )}
        {activeDockAssignment && !readOnly ? (
          <form
            className="loadout-dock-arrival-form mt-3 flex flex-wrap items-end gap-2 rounded-xl border border-white/10 bg-white/5 p-3"
            onSubmit={(formEvent) => {
              formEvent.preventDefault();
              void addDockVehicle(activeDockAssignment);
            }}
          >
            <label className="grid gap-1 text-xs font-bold text-slate-200">
              Vehicle arriving at dock
              <input
                className="rounded-lg border border-white/20 bg-slate-950 px-3 py-2 text-sm text-white"
                onChange={(inputEvent) =>
                  setDockVehicleLabel(inputEvent.currentTarget.value)
                }
                placeholder="Truck 1, Van 1, or plate"
                value={dockVehicleLabel}
              />
            </label>
            <button
              className="rounded-lg bg-amber-300 px-3 py-2 text-sm font-bold text-slate-950 disabled:opacity-50"
              disabled={vehicleBusy || !dockVehicleLabel.trim()}
              type="submit"
            >
              Add vehicle
            </button>
          </form>
        ) : null}
      </section>

      <div className="mt-4 grid gap-4 xl:grid-cols-[1.2fr_0.8fr]">
        <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div>
              <p className="brand-eyebrow text-blue-200">Loadout zones</p>
              <h5 className="font-bold">Live store map</h5>
            </div>
            <div className="flex flex-wrap gap-2 text-xs">
              {[
                ["not_started", "Not started"],
                ["in_progress", "In progress"],
                ["exceptions_present", "Exceptions"],
                ["signed_complete", "Ready"],
                ["released_from_venue", "Released"],
              ].map(([status, label]) => (
                <span className="flex items-center gap-1" key={status}>
                  <i
                    className={`h-2.5 w-2.5 rounded-full ${statusDot(status)}`}
                  />
                  {label}
                </span>
              ))}
            </div>
          </div>
          <div className="mt-4 grid gap-3 md:grid-cols-2">
            {zoneGroups.map(([zone, zoneAssignments]) => (
              <section
                className="rounded-xl border border-white/10 bg-slate-900/80 p-3"
                key={zone}
              >
                <div className="flex items-center justify-between gap-2">
                  <h6 className="font-bold">{zone}</h6>
                  <span className="text-xs text-slate-300">
                    {zoneAssignments.length} store
                    {zoneAssignments.length === 1 ? "" : "s"}
                  </span>
                </div>
                <div className="mt-3 grid gap-2">
                  {zoneAssignments.map((assignment) => (
                    <article
                      className="loadout-zone-store-row grid grid-cols-[auto_1fr_auto] items-center gap-2 rounded-lg bg-white/8 p-2 text-sm"
                      key={assignment.id}
                    >
                      <i
                        className={`h-3 w-3 rounded-full ${statusDot(
                          assignment.status,
                        )}`}
                      />
                      <div>
                        <strong>Store {assignment.store_number}</strong>
                        <p className="text-xs text-slate-300">
                          {assignment.item_count} item
                          {assignment.item_count === 1 ? "" : "s"} · depart{" "}
                          {displayDateTime(assignment.recommended_departure_at)}
                        </p>
                        <p className="text-xs text-amber-200">
                          Vehicles:{" "}
                          {assignment.vehicle_labels
                            .map(
                              (vehicle) =>
                                `${vehicle} (${assignment.vehicle_statuses[vehicle] ?? "expected"})`,
                            )
                            .join(", ") || "Truck 1 (expected)"}
                        </p>
                      </div>
                      <span className="text-right text-xs capitalize text-slate-200">
                        {statusLabel(assignment.status)}
                      </span>
                    </article>
                  ))}
                </div>
              </section>
            ))}
            {!zoneGroups.length ? (
              <p className="rounded-xl border border-dashed border-white/20 p-5 text-slate-300 md:col-span-2">
                No store loadout assignments exist yet.
              </p>
            ) : null}
          </div>
        </div>

        <div className="grid gap-4">
          <section className="rounded-2xl border border-white/10 bg-white/5 p-4">
            <p className="brand-eyebrow text-blue-200">Booth clearance</p>
            <h5 className="font-bold">Assigned inventory leaving booths</h5>
            <div className="mt-3 grid gap-2">
              {boothSummary.slice(0, 8).map(([booth, counts]) => {
                const releasedPercent = counts.assigned
                  ? Math.round((counts.released / counts.assigned) * 100)
                  : 0;
                return (
                  <article className="rounded-lg bg-white/8 p-3" key={booth}>
                    <div className="flex justify-between gap-2 text-sm">
                      <strong>Booth {booth}</strong>
                      <span>{releasedPercent}% released</span>
                    </div>
                    <div className="mt-2 h-2 overflow-hidden rounded-full bg-white/10">
                      <span
                        className="block h-full rounded-full bg-green-400"
                        style={{ width: `${releasedPercent}%` }}
                      />
                    </div>
                    <p className="mt-2 text-xs text-slate-300">
                      Assigned {counts.assigned} · found {counts.found} ·
                      exceptions {counts.exceptions}
                    </p>
                  </article>
                );
              })}
              {!boothSummary.length ? (
                <p className="rounded-xl border border-dashed border-white/20 p-4 text-sm text-slate-300">
                  Booth clearance appears after store assignments are created.
                </p>
              ) : null}
            </div>
          </section>

          <section className="rounded-2xl border border-white/10 bg-white/5 p-4">
            <p className="brand-eyebrow text-blue-200">Exception queue</p>
            <h5 className="font-bold">Needs admin attention</h5>
            <div className="mt-3 grid gap-2">
              {exceptionAssignments.slice(0, 6).map((assignment) => (
                <article
                  className="rounded-lg border border-red-300/20 bg-red-500/10 p-3 text-sm"
                  key={assignment.id}
                >
                  <strong>Store {assignment.store_number}</strong>
                  <p className="text-xs text-red-100">
                    {assignment.exception_count} exception
                    {assignment.exception_count === 1 ? "" : "s"} ·{" "}
                    {assignment.loadout_zone ?? "No zone"}
                  </p>
                </article>
              ))}
              {!exceptionAssignments.length ? (
                <p className="rounded-xl border border-dashed border-white/20 p-4 text-sm text-slate-300">
                  No active loadout exceptions.
                </p>
              ) : null}
            </div>
          </section>
        </div>
      </div>
    </section>
  );
}

function LiveQueue({
  label,
  value,
  tone,
}: {
  label: string;
  value: number;
  tone: "green" | "red" | "yellow";
}) {
  const toneClass =
    tone === "green"
      ? "bg-green-300 text-green-950"
      : tone === "red"
        ? "bg-red-300 text-red-950"
        : "bg-yellow-300 text-yellow-950";
  return (
    <div className={`rounded-xl px-3 py-2 font-bold ${toneClass}`}>
      <span className="block text-lg leading-none">{value}</span>
      <span className="text-[0.65rem] uppercase tracking-wide">{label}</span>
    </div>
  );
}

function statusDot(status: string) {
  if (status === "released_from_venue") return "bg-green-400";
  if (status === "signed_complete") return "bg-emerald-300";
  if (status === "ready_for_final_review") return "bg-blue-300";
  if (status === "exceptions_present") return "bg-red-400";
  if (status === "in_progress") return "bg-yellow-300";
  return "bg-slate-400";
}
