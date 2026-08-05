"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
import { VendorHallLiveMap } from "@/components/VendorHallLiveMap";
import { ManagedEvent } from "@/lib/event-admin-api";
import { useAuth } from "@/lib/auth";
import { hasPermission } from "@/lib/permissions";
import {
  configureVendorHall,
  forceCloseVendorHall,
  exportVendorHallReport,
  getVendorHallFloorMapStatus,
  getVendorHallFloorMapContent,
  getVendorHallSummary,
  listVendorHallBooths,
  importVendorHallFloorMapPdf,
  assignVendorHallBoothStaff,
  syncVendorHallBooths,
  updateVendorHallBoothMapPosition,
  VendorHallBooth,
  VendorHallExportReport,
  VendorHallFloorMapStatus,
  VendorHallSummary,
} from "@/lib/vendor-hall-api";

const statusLabels: Record<string, string> = {
  draft: "Not submitted",
  inventory_submitted: "Inventory submitted",
  ready_for_inspection: "Ready for inspection",
  checkin_in_progress: "Check-in in progress",
  fully_checked_in: "Fully checked in",
  exceptions_present: "Exceptions present",
  admin_reviewed: "Admin reviewed",
  closed: "Closed",
};

const statusClasses: Record<string, string> = {
  draft: "bg-slate-200 text-slate-800",
  inventory_submitted: "bg-blue-100 text-blue-800",
  ready_for_inspection: "bg-yellow-100 text-yellow-900",
  checkin_in_progress: "bg-red-100 text-red-800",
  fully_checked_in: "bg-green-100 text-green-800",
  exceptions_present: "bg-red-100 text-red-800",
  admin_reviewed: "bg-purple-100 text-purple-800",
  closed: "bg-slate-950 text-white",
};

const exportReports: Array<{ type: VendorHallExportReport; label: string }> = [
  { type: "full-inventory", label: "Full inventory" },
  { type: "available-for-sale", label: "Available for sale" },
  { type: "damaged-items", label: "Damaged items" },
  { type: "missing-items", label: "Missing items" },
  { type: "vendor-summary", label: "Vendor summary" },
  { type: "booth-completion", label: "Completion report" },
  { type: "staff-checkin-log", label: "Staff activity log" },
];

export function VendorHallSetupPanel({ event }: { event: ManagedEvent }) {
  const [summary, setSummary] = useState<VendorHallSummary | null>(null);
  const [booths, setBooths] = useState<VendorHallBooth[]>([]);
  const [mapStatus, setMapStatus] = useState<VendorHallFloorMapStatus | null>(
    null,
  );
  const [busy, setBusy] = useState(false);
  const [floorMapUrl, setFloorMapUrl] = useState<string | null>(null);
  const [placementBoothId, setPlacementBoothId] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const { user } = useAuth();
  const canOverrideClose = Boolean(user && hasPermission(user, "system.admin"));
  const staffMembers = event.memberships.filter((member) =>
    ["staff", "admin"].includes(member.membership_type),
  );

  const load = useCallback(async () => {
    const [nextSummary, nextBooths, nextMapStatus] = await Promise.all([
      getVendorHallSummary(event.id),
      listVendorHallBooths(event.id),
      getVendorHallFloorMapStatus(event.id),
    ]);
    setSummary(nextSummary);
    setBooths(nextBooths);
    setMapStatus(nextMapStatus);
  }, [event.id]);

  useEffect(() => {
    setMessage(null);
    setError(null);
    void load().catch((caught: unknown) =>
      setError(
        caught instanceof Error
          ? caught.message
          : "Unable to load the vendor hall.",
      ),
    );
  }, [load]);

  useEffect(() => {
    let active = true;
    let url: string | null = null;
    setFloorMapUrl(null);
    if (mapStatus?.floor_map?.has_image) {
      void getVendorHallFloorMapContent(event.id, true)
        .then((blob) => {
          if (!active) return;
          url = URL.createObjectURL(blob);
          setFloorMapUrl(url);
        })
        .catch(() => undefined);
    }
    return () => {
      active = false;
      if (url) URL.revokeObjectURL(url);
    };
  }, [
    event.id,
    mapStatus?.floor_map?.has_image,
    mapStatus?.floor_map?.uploaded_at,
  ]);

  async function action(work: () => Promise<unknown>, success: string) {
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      await work();
      await load();
      setMessage(success);
    } catch (caught) {
      setError(
        caught instanceof Error ? caught.message : "Vendor hall action failed.",
      );
    } finally {
      setBusy(false);
    }
  }

  function importFloorMap(formEvent: FormEvent<HTMLFormElement>) {
    formEvent.preventDefault();
    const data = new FormData(formEvent.currentTarget);
    const file = data.get("file");
    if (!(file instanceof File) || !file.size) return;
    void action(
      () =>
        importVendorHallFloorMapPdf(event.id, String(data.get("name")), file),
      "Floor plan imported and booth labels scanned.",
    );
  }

  function placeBooth(x: number, y: number) {
    if (!placementBoothId) return;
    void action(
      () =>
        updateVendorHallBoothMapPosition(event.id, placementBoothId, {
          floor_map_zone: "PDF review placement",
          map_x: x.toFixed(4),
          map_y: y.toFixed(4),
          map_width: "8",
          map_height: "6",
        }),
      "Booth placed on the imported floor plan.",
    ).then(() => setPlacementBoothId(""));
  }

  return (
    <section className="event-ui rounded-2xl border bg-white p-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="brand-eyebrow">021 · Vendor Hall Setup</p>
          <h3 className="text-xl font-bold">Vendor hall inventory setup</h3>
          <p className="mt-1 text-sm text-slate-600">
            Convert event vendor booth profiles into live vendor hall booths,
            monitor submissions, and prepare staff check-in.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <button
            className="rounded-xl border border-yellow-500 px-4 py-2 font-bold text-yellow-300"
            onClick={() =>
              document
                .getElementById("vendor-hall-floor-plan-import")
                ?.scrollIntoView({ behavior: "smooth", block: "start" })
            }
            type="button"
          >
            Import floor plan PDF
          </button>
          <button
            className="rounded-xl border px-4 py-2 font-bold disabled:bg-slate-100"
            disabled={busy}
            onClick={() =>
              action(
                () =>
                  configureVendorHall(event.id, {
                    status: "open",
                    allow_vendor_edits_after_submission: false,
                    require_staff_checkin: true,
                  }),
                "Vendor hall opened for this event.",
              )
            }
            type="button"
          >
            Open hall
          </button>
          <button
            className="rounded-xl bg-blue-800 px-4 py-2 font-bold text-white disabled:bg-slate-400"
            disabled={busy}
            onClick={() =>
              action(
                () => syncVendorHallBooths(event.id),
                "Vendor booths synced into vendor hall.",
              )
            }
            type="button"
          >
            Sync vendor booths
          </button>
          <button
            className="rounded-xl bg-green-700 px-4 py-2 font-bold text-white disabled:bg-slate-300"
            disabled={busy || !summary?.closeout_ready}
            onClick={() =>
              action(
                () =>
                  configureVendorHall(event.id, {
                    status: "closed",
                    allow_vendor_edits_after_submission: false,
                    require_staff_checkin: true,
                  }),
                "Vendor hall closed out successfully.",
              )
            }
            type="button"
          >
            Close vendor hall
          </button>
          {canOverrideClose ? (
            <button
              className="rounded-xl border border-red-500 px-4 py-2 font-bold text-red-700 disabled:bg-slate-100"
              disabled={busy || summary?.closeout_ready}
              onClick={() =>
                window.confirm(
                  "Force-close this Vendor Hall as a system-admin exception? Incomplete booth work will remain in the audit history.",
                )
                  ? void action(
                      () => forceCloseVendorHall(event.id),
                      "System admin override closed the vendor hall.",
                    )
                  : undefined
              }
              type="button"
            >
              System admin override
            </button>
          ) : null}
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
      <div className="mt-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
        <Metric label="Booths" value={summary?.booth_total ?? 0} />
        <Metric label="Submitted" value={summary?.inventory_submitted ?? 0} />
        <Metric label="In check-in" value={summary?.checkin_in_progress ?? 0} />
        <Metric label="Complete" value={summary?.fully_checked_in ?? 0} />
        <Metric label="Exceptions" value={summary?.exceptions_present ?? 0} />
        <Metric
          label="Setup complete %"
          value={`${summary?.completion_percentage ?? "0.00"}%`}
        />
      </div>
      <div className="mt-4 grid gap-3 rounded-xl border bg-slate-50 p-4 sm:grid-cols-2">
        <ProgressMetric
          label="Booths fully checked in"
          value={`${summary?.completion_percentage ?? "0.00"}%`}
          detail={`${summary?.fully_checked_in ?? 0} of ${summary?.booth_total ?? 0} booths`}
        />
        <ProgressMetric
          label="Inventory items checked"
          value={`${summary?.inventory_completion_percentage ?? "0.00"}%`}
          detail={`${summary?.inventory_items_checked ?? 0} of ${summary?.inventory_item_total ?? 0} items`}
        />
      </div>
      <div className="mt-4 overflow-hidden rounded-xl border">
        <div className="grid grid-cols-[1.2fr_0.8fr_0.8fr_0.8fr_1.1fr] gap-3 bg-slate-50 p-3 text-xs font-bold uppercase text-slate-500">
          <span>Vendor booth</span>
          <span>Status</span>
          <span>Inventory</span>
          <span>For sale</span>
          <span>Inspection staff</span>
        </div>
        {booths.map((booth) => (
          <article
            className="grid grid-cols-[1.2fr_0.8fr_0.8fr_0.8fr_1.1fr] gap-3 border-t p-3 text-sm"
            key={booth.id}
          >
            <div>
              <strong className="block">{booth.booth_name}</strong>
              <span className="text-slate-500">
                {booth.vendor_name ?? booth.vendor_code} · Booth{" "}
                {booth.booth_number || "TBD"}
              </span>
            </div>
            <span
              className={`h-fit rounded-full px-3 py-1 text-xs font-bold ${statusClasses[booth.status] ?? "bg-slate-100 text-slate-700"}`}
            >
              {statusLabels[booth.status] ?? booth.status}
            </span>
            <span>{booth.inventory_count}</span>
            <span>{booth.available_for_sale_count}</span>
            <select
              aria-label={`Assign inspection staff for ${booth.booth_name}`}
              className="rounded-lg border bg-white p-2 text-xs"
              disabled={busy}
              onChange={(input) =>
                void action(
                  () =>
                    assignVendorHallBoothStaff(
                      event.id,
                      booth.id,
                      input.target.value || null,
                    ),
                  "Inspection staff assignment saved.",
                )
              }
              value={booth.assigned_staff_membership_id ?? ""}
            >
              <option value="">Unassigned</option>
              {staffMembers.map((member) => (
                <option key={member.id} value={member.id}>
                  {member.display_name}
                </option>
              ))}
            </select>
          </article>
        ))}
        {!booths.length ? (
          <p className="border-t p-5 text-sm text-slate-500">
            No vendor hall booths yet. Create vendor booth profiles first, then
            sync them into the vendor hall.
          </p>
        ) : null}
      </div>
      <section className="mt-5 rounded-2xl border bg-white p-4">
        <p className="brand-eyebrow">Reports / Exports</p>
        <h3 className="text-lg font-bold">Vendor hall exports</h3>
        <p className="mt-1 text-sm text-slate-600">
          Download operational CSV reports for purchasing review, vendor
          follow-up, and staff accountability.
        </p>
        <div className="mt-4 flex flex-wrap gap-2">
          {exportReports.map((report) => (
            <button
              className="rounded-lg border px-3 py-2 text-sm font-bold"
              disabled={busy}
              key={report.type}
              onClick={() =>
                void action(
                  () => exportVendorHallReport(event.id, report.type),
                  `${report.label} exported.`,
                )
              }
              type="button"
            >
              {report.label}
            </button>
          ))}
        </div>
      </section>
      <section
        className="mt-5 scroll-mt-24 rounded-2xl border border-yellow-500/40 bg-slate-50 p-4"
        id="vendor-hall-floor-plan-import"
      >
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <p className="brand-eyebrow">Floor plan PDF import</p>
            <h3 className="text-lg font-bold">
              {mapStatus?.floor_map?.name ?? "No floor map configured"}
            </h3>
            <p className="text-sm text-slate-600">
              Upload the venue PDF. BTSP scans text-based booth labels and
              positions matching booths on the interactive status map.
            </p>
          </div>
        </div>
        <form
          className="mt-4 grid gap-3 md:grid-cols-[1fr_1fr_auto]"
          onSubmit={importFloorMap}
        >
          <input
            className="rounded-lg border bg-white p-3"
            defaultValue={
              mapStatus?.floor_map?.name ?? `${event.name} floor plan`
            }
            name="name"
            placeholder="Map name"
            required
          />
          <input
            accept="application/pdf,.pdf"
            className="rounded-lg border bg-white p-3"
            name="file"
            required
            type="file"
          />
          <button
            className="rounded-xl bg-blue-800 px-4 py-2 font-bold text-white disabled:bg-slate-400"
            disabled={busy}
          >
            Import and scan PDF
          </button>
        </form>
        {mapStatus?.floor_map ? (
          <div className="mt-3 grid gap-2 text-sm sm:grid-cols-3">
            <Metric
              label="Detected booths"
              value={String(
                mapStatus.floor_map.layout_json.detected_booth_count ?? 0,
              )}
            />
            <Metric
              label="Needs review"
              value={String(
                mapStatus.floor_map.layout_json.unmatched_booth_count ??
                  booths.length,
              )}
            />
            <Metric
              label="PDF pages"
              value={String(mapStatus.floor_map.layout_json.page_count ?? 0)}
            />
          </div>
        ) : null}
        <p className="mt-3 text-xs text-slate-500">
          Automatic placement works with text-based PDF floor plans. Image-only
          scans remain available as the map background but may require a future
          OCR pass before booths can be detected.
        </p>
        {mapStatus?.floor_map && booths.length ? (
          <div className="mt-3 rounded-xl border p-3">
            <label className="text-sm font-bold">
              Review or correct a booth position
              <select
                className="mt-1"
                onChange={(input) => setPlacementBoothId(input.target.value)}
                value={placementBoothId}
              >
                <option value="">
                  Select a booth, then click its PDF location
                </option>
                {booths.map((booth) => (
                  <option key={booth.id} value={booth.id}>
                    {booth.booth_number || "No number"} — {booth.booth_name}
                    {booth.map_x === null ? " (unmatched)" : " (reposition)"}
                  </option>
                ))}
              </select>
            </label>
          </div>
        ) : null}
        <VendorHallLiveMap
          mapStatus={mapStatus}
          onPlace={placeBooth}
          placementBoothId={placementBoothId}
          sourceUrl={floorMapUrl}
        />
      </section>
    </section>
  );
}

function Metric({ label, value }: { label: string; value: number | string }) {
  return (
    <div className="rounded-xl bg-slate-50 p-4">
      <span className="block text-xs font-bold uppercase text-slate-500">
        {label}
      </span>
      <strong className="text-2xl">{value}</strong>
    </div>
  );
}

function ProgressMetric({
  label,
  value,
  detail,
}: {
  label: string;
  value: string;
  detail: string;
}) {
  return (
    <div>
      <div className="flex justify-between gap-2 text-sm font-bold">
        <span>{label}</span>
        <span>{value}</span>
      </div>
      <div className="mt-2 h-2 overflow-hidden rounded-full bg-slate-200">
        <div
          className="h-full rounded-full bg-green-600"
          style={{ width: value }}
        />
      </div>
      <p className="mt-1 text-xs text-slate-500">{detail}</p>
    </div>
  );
}
