"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
import { VendorHallLiveMap } from "@/components/VendorHallLiveMap";
import { ManagedEvent } from "@/lib/event-admin-api";
import {
  getVendorHallFloorMapContent,
  getVendorHallFloorMapStatus,
  importVendorHallFloorMapPdf,
  syncVendorHallBooths,
  updateVendorHallBoothMapPosition,
  VendorHallFloorMapStatus,
} from "@/lib/vendor-hall-api";

export function VendorHallFloorPlanUploadPanel({
  event,
}: {
  event: ManagedEvent;
}) {
  const [status, setStatus] = useState<VendorHallFloorMapStatus | null>(null);
  const [sourceUrl, setSourceUrl] = useState<string | null>(null);
  const [placementBoothId, setPlacementBoothId] = useState("");
  const [boundaryX, setBoundaryX] = useState("50");
  const [boundaryY, setBoundaryY] = useState("50");
  const [boundaryWidth, setBoundaryWidth] = useState("8");
  const [boundaryHeight, setBoundaryHeight] = useState("6");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setStatus(await getVendorHallFloorMapStatus(event.id));
  }, [event.id]);

  useEffect(() => {
    void load().catch((caught: unknown) =>
      setError(
        caught instanceof Error
          ? caught.message
          : "Unable to load the floor plan.",
      ),
    );
  }, [load]);

  useEffect(() => {
    let active = true;
    let url: string | null = null;
    setSourceUrl(null);
    if (status?.floor_map?.has_image) {
      void getVendorHallFloorMapContent(event.id, true).then((blob) => {
        if (!active) return;
        url = URL.createObjectURL(blob);
        setSourceUrl(url);
      });
    }
    return () => {
      active = false;
      if (url) URL.revokeObjectURL(url);
    };
  }, [event.id, status?.floor_map?.has_image, status?.floor_map?.uploaded_at]);

  async function run(work: () => Promise<unknown>, success: string) {
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      await work();
      await load();
      setMessage(success);
    } catch (caught) {
      setError(
        caught instanceof Error ? caught.message : "Floor plan action failed",
      );
    } finally {
      setBusy(false);
    }
  }

  function upload(formEvent: FormEvent<HTMLFormElement>) {
    formEvent.preventDefault();
    const data = new FormData(formEvent.currentTarget);
    const file = data.get("file");
    if (!(file instanceof File) || !file.size) return;
    void run(
      () =>
        importVendorHallFloorMapPdf(event.id, String(data.get("name")), file),
      "Floor plan imported and scanned.",
    );
  }

  function place(x: number, y: number) {
    if (!placementBoothId) return;
    setBoundaryX(x.toFixed(4));
    setBoundaryY(y.toFixed(4));
    void run(
      () =>
        updateVendorHallBoothMapPosition(event.id, placementBoothId, {
          floor_map_zone: "PDF review placement",
          map_x: x.toFixed(4),
          map_y: y.toFixed(4),
          map_width: boundaryWidth,
          map_height: boundaryHeight,
        }),
      "Booth position saved.",
    );
  }

  function saveBoundarySize() {
    const booth = booths.find((item) => item.id === placementBoothId);
    if (!booth || booth.map_x === null || booth.map_y === null) return;
    void run(
      () =>
        updateVendorHallBoothMapPosition(event.id, booth.id, {
          floor_map_zone: booth.floor_map_zone ?? "Manual boundary adjustment",
          map_x: boundaryX,
          map_y: boundaryY,
          map_width: boundaryWidth,
          map_height: boundaryHeight,
        }),
      "Booth boundary size saved as a manual override.",
    );
  }

  function syncBooths() {
    void run(
      () => syncVendorHallBooths(event.id),
      "Vendor booths synced and the active floor plan was rescanned.",
    );
  }

  const booths = status?.booths ?? [];
  const layout = status?.floor_map?.layout_json ?? {};
  const hasUploadedMap = Boolean(status?.floor_map);
  const hasBooths = booths.length > 0;
  const detectedCount = Number(layout.detected_booth_count ?? 0);
  const textFragmentCount = Number(layout.text_fragment_count ?? 0);

  return (
    <section className="event-ui rounded-2xl border border-yellow-500/50 bg-slate-50 p-5">
      <p className="brand-eyebrow">Vendor Hall floor plan</p>
      <h3 className="text-2xl font-bold">
        Upload and digitize a floor-plan PDF
      </h3>
      <p className="mt-1 text-sm text-slate-600">
        Upload the venue PDF here. Booth profiles should be created and synced
        before scanning.
      </p>
      {message ? (
        <p className="mt-3 rounded-xl bg-green-50 p-3 text-green-800">
          {message}
        </p>
      ) : null}
      {error ? (
        <p className="mt-3 rounded-xl bg-red-50 p-3 text-red-800">{error}</p>
      ) : null}
      <form
        className="mt-5 grid gap-3 md:grid-cols-[1fr_1fr_auto]"
        onSubmit={upload}
      >
        <label className="font-bold">
          Floor-plan name
          <input
            className="mt-1 rounded-xl border p-3"
            defaultValue={status?.floor_map?.name ?? `${event.name} floor plan`}
            name="name"
            required
          />
        </label>
        <label className="font-bold">
          PDF file
          <input
            accept="application/pdf,.pdf"
            className="mt-1 rounded-xl border p-3"
            name="file"
            required
            type="file"
          />
        </label>
        <button
          className="self-end rounded-xl bg-blue-800 px-5 py-3 font-bold text-white disabled:bg-slate-400"
          disabled={busy}
        >
          {busy ? "Processing…" : "Import and scan PDF"}
        </button>
      </form>
      {status?.floor_map ? (
        <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <Metric
            label="Detected"
            value={String(layout.detected_booth_count ?? 0)}
          />
          <Metric
            label="Measured geometry"
            value={String(layout.measured_geometry_count ?? 0)}
          />
          <Metric
            label="Fallback geometry"
            value={String(layout.fallback_geometry_count ?? 0)}
          />
          <Metric
            label="Needs review"
            value={String(layout.unmatched_booth_count ?? booths.length)}
          />
        </div>
      ) : null}
      {Array.isArray(layout.review_reasons) && layout.review_reasons.length ? (
        <div className="floor-plan-review-warning mt-4 rounded-xl border p-4 text-sm">
          <strong className="block">Automatic analysis needs review</strong>
          <ul className="mt-2 list-disc space-y-1 pl-5">
            {layout.review_reasons.map((reason, index) => (
              <li key={`${String(reason)}-${index}`}>{String(reason)}</li>
            ))}
          </ul>
        </div>
      ) : null}
      {hasUploadedMap && !hasBooths ? (
        <div className="floor-plan-review-warning mt-4 rounded-xl border p-4 text-sm">
          <strong className="block">
            No vendor hall booths are available to place yet.
          </strong>
          <span className="mt-1 block">
            Create vendor booth profiles for this event, then sync them here.
            BTSP will rescan this uploaded PDF and place matching booth numbers
            automatically.
          </span>
          <button
            className="mt-3 rounded-xl bg-blue-800 px-4 py-2 font-bold text-white disabled:bg-slate-400"
            disabled={busy}
            onClick={syncBooths}
            type="button"
          >
            Sync vendor booths and rescan
          </button>
        </div>
      ) : null}
      {hasUploadedMap && hasBooths && detectedCount === 0 ? (
        <div className="floor-plan-review-warning mt-4 rounded-xl border p-4 text-sm">
          <strong className="block">
            The PDF uploaded, but no booth labels matched.
          </strong>
          <span className="mt-1 block">
            The scan found {textFragmentCount} PDF text fragments. Confirm the
            booth profile numbers match the floor-plan labels, or select a booth
            below and click its location manually.
          </span>
        </div>
      ) : null}
      {hasUploadedMap && hasBooths ? (
        <div className="mt-4 rounded-xl border p-3 text-sm">
          <label className="block font-bold">
            Review or correct a booth position
            <select
              className="mt-1"
              onChange={(input) => {
                const booth = booths.find(
                  (item) => item.id === input.target.value,
                );
                setPlacementBoothId(input.target.value);
                setBoundaryX(booth?.map_x ?? "50");
                setBoundaryY(booth?.map_y ?? "50");
                setBoundaryWidth(booth?.map_width ?? "8");
                setBoundaryHeight(booth?.map_height ?? "6");
              }}
              value={placementBoothId}
            >
              <option value="">
                Select a booth, then click its location below
              </option>
              {booths.map((booth) => (
                <option key={booth.id} value={booth.id}>
                  {booth.booth_number || "No number"} — {booth.booth_name}
                  {booth.map_x === null ? " (unmatched)" : " (reposition)"}
                </option>
              ))}
            </select>
          </label>
          {placementBoothId ? (
            <div className="mt-3 grid gap-3 rounded-xl bg-slate-100 p-3 sm:grid-cols-2 lg:grid-cols-5">
              <label className="font-bold">
                Left (% of room)
                <input
                  className="mt-1 w-full rounded-lg border bg-white p-2"
                  max="96"
                  min="0"
                  onChange={(input) => setBoundaryX(input.target.value)}
                  step="0.25"
                  type="number"
                  value={boundaryX}
                />
              </label>
              <label className="font-bold">
                Top (% of room)
                <input
                  className="mt-1 w-full rounded-lg border bg-white p-2"
                  max="92"
                  min="0"
                  onChange={(input) => setBoundaryY(input.target.value)}
                  step="0.25"
                  type="number"
                  value={boundaryY}
                />
              </label>
              <label className="font-bold">
                Booth width (% of room)
                <input
                  className="mt-1 w-full rounded-lg border bg-white p-2"
                  max="100"
                  min="1"
                  onChange={(input) => setBoundaryWidth(input.target.value)}
                  step="0.25"
                  type="number"
                  value={boundaryWidth}
                />
              </label>
              <label className="font-bold">
                Booth height (% of room)
                <input
                  className="mt-1 w-full rounded-lg border bg-white p-2"
                  max="100"
                  min="1"
                  onChange={(input) => setBoundaryHeight(input.target.value)}
                  step="0.25"
                  type="number"
                  value={boundaryHeight}
                />
              </label>
              <button
                className="self-end rounded-lg bg-blue-800 px-4 py-2 font-bold text-white disabled:bg-slate-400 sm:col-span-2 lg:col-span-1"
                disabled={busy}
                onClick={saveBoundarySize}
                type="button"
              >
                Save position & size
              </button>
              <p className="text-xs text-slate-600 sm:col-span-2 lg:col-span-3">
                Adjust the footprint here, or click the map to reposition it.
                Manual overrides are preserved when vendor booths are
                synchronized.
              </p>
            </div>
          ) : null}
        </div>
      ) : null}
      <VendorHallLiveMap
        mapStatus={status}
        onPlace={place}
        placementBoothId={placementBoothId}
        sourceUrl={sourceUrl}
      />
    </section>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl bg-slate-50 p-4">
      <span className="block text-xs font-bold uppercase text-slate-500">
        {label}
      </span>
      <strong className="text-2xl">{value}</strong>
    </div>
  );
}
