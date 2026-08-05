"use client";

import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import { useAuth } from "@/lib/auth";
import { ManagedEvent, listMyEvents } from "@/lib/event-admin-api";
import { hasAnyPermission } from "@/lib/permissions";
import { VendorHallLiveMap } from "@/components/VendorHallLiveMap";
import {
  checkinVendorHallInventoryItem,
  completeVendorHallBoothCheckin,
  createVendorHallInventoryItem,
  deleteVendorHallItemAttachment,
  downloadVendorHallItemAttachment,
  importVendorHallInventory,
  listMyVendorHallBooths,
  listVendorHallBooths,
  listVendorHallInventory,
  getVendorHallFloorMapContent,
  getVendorHallFloorMapStatus,
  markVendorHallBoothReadyForInspection,
  startVendorHallBoothCheckin,
  submitVendorHallInventory,
  splitVendorHallInventoryItem,
  updateVendorHallInventoryItem,
  updateVendorHallInventoryItemStaff,
  uploadVendorHallItemAttachment,
  VendorHallBooth,
  VendorHallInventoryItem,
  VendorHallInventoryItemWrite,
  VendorHallItemCondition,
  VendorHallItemAttachment,
  VendorHallItemStatus,
  VendorHallFloorMapStatus,
} from "@/lib/vendor-hall-api";

const itemStatuses: VendorHallItemStatus[] = [
  "expected",
  "checked_in",
  "damaged",
  "not_in_booth",
  "removed",
];

const conditions: VendorHallItemCondition[] = [
  "new",
  "floor_model",
  "open_box",
  "used",
  "damaged",
  "unknown",
];

function itemPayload(data: FormData): VendorHallInventoryItemWrite {
  const availableForSale = data.get("available_for_sale") === "on";
  return {
    item_name: String(data.get("item_name")),
    model_number: String(data.get("model_number") || "") || null,
    serial_number: String(data.get("serial_number") || "") || null,
    description: String(data.get("description") || "") || null,
    quantity_expected: Number(data.get("quantity_expected")) || 1,
    unit_price: String(data.get("unit_price") || "") || null,
    currency: "USD",
    condition: String(data.get("condition")) as VendorHallItemCondition,
    status: "expected",
    available_for_sale: availableForSale,
    sell_to_buddys_price: availableForSale
      ? String(data.get("sell_to_buddys_price") || "") || null
      : null,
    notes: String(data.get("notes") || "") || null,
    vendor_notes: String(data.get("vendor_notes") || "") || null,
  };
}

export function VendorHallOperationsPanel({
  event,
  compact = false,
}: {
  event?: ManagedEvent;
  compact?: boolean;
}) {
  const { user } = useAuth();
  const elevatedStaff = Boolean(
    user?.roles.some((role) => ["ADMIN", "SYSTEM_ADMIN"].includes(role)),
  );
  const eventMembershipType = event?.memberships.find(
    (membership) =>
      membership.email.toLowerCase() === user?.email?.toLowerCase(),
  )?.membership_type;
  const staffScoped = Boolean(
    eventMembershipType === "staff" ||
      (user?.roles.includes("EVENT_STAFF") && !elevatedStaff),
  );
  const canManageVendorInventory =
    !staffScoped &&
    hasAnyPermission(user, ["vendor_hall.vendor.manage", "vendor_hall.manage"]);
  const canCheckIn = hasAnyPermission(user, [
    "vendor_hall.staff.checkin",
    "vendor_hall.manage",
  ]);
  const vendorScoped = Boolean(user?.roles.includes("VENDOR"));
  const staffScopedToAssignments = Boolean(
    staffScoped || (!vendorScoped && canCheckIn && !canManageVendorInventory),
  );
  const canSeeLiveMap = Boolean(
    event && (elevatedStaff || staffScopedToAssignments),
  );
  const [booths, setBooths] = useState<VendorHallBooth[]>([]);
  const [mapStatus, setMapStatus] = useState<VendorHallFloorMapStatus | null>(
    null,
  );
  const [floorMapUrl, setFloorMapUrl] = useState<string | null>(null);
  const [selectedBoothId, setSelectedBoothId] = useState<string | null>(null);
  const [boothSearch, setBoothSearch] = useState("");
  const [items, setItems] = useState<VendorHallInventoryItem[]>([]);
  const [validatedItemIds, setValidatedItemIds] = useState<Set<string>>(
    () => new Set(),
  );
  const [openItemId, setOpenItemId] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const selectedBooth = useMemo(
    () => booths.find((booth) => booth.id === selectedBoothId) ?? booths[0],
    [booths, selectedBoothId],
  );
  const boothLocked = Boolean(
    selectedBooth &&
      (Boolean(selectedBooth.checkin_completed_at) ||
        ["fully_checked_in", "admin_reviewed"].includes(selectedBooth.status)),
  );
  const filteredBooths = useMemo(() => {
    const query = boothSearch.trim().toLowerCase();
    if (!query) return booths;
    return booths.filter((booth) =>
      [
        booth.booth_name,
        booth.vendor_name,
        booth.vendor_code,
        booth.booth_number,
      ]
        .filter(Boolean)
        .some((value) => String(value).toLowerCase().includes(query)),
    );
  }, [boothSearch, booths]);
  const visibleMapStatus = useMemo(() => {
    if (!mapStatus || !staffScopedToAssignments) return mapStatus;
    const assignedIds = new Set(booths.map((booth) => booth.id));
    return {
      ...mapStatus,
      booths: mapStatus.booths.filter((booth) => assignedIds.has(booth.id)),
    };
  }, [booths, mapStatus, staffScopedToAssignments]);

  function searchBooths(value: string) {
    setBoothSearch(value);
    const query = value.trim().toLowerCase();
    if (!query) return;
    const firstMatch = booths.find((booth) =>
      [
        booth.booth_name,
        booth.vendor_name,
        booth.vendor_code,
        booth.booth_number,
      ]
        .filter(Boolean)
        .some((field) => String(field).toLowerCase().includes(query)),
    );
    if (firstMatch) setSelectedBoothId(firstMatch.id);
  }

  const loadBooths = useCallback(async () => {
    // Vendor sessions must always use the server-scoped /mine collection,
    // even when a parent event prop is supplied by a sub-event workspace.
    if (vendorScoped || staffScopedToAssignments)
      return listMyVendorHallBooths();
    if (event) return listVendorHallBooths(event.id);
    if (canCheckIn) {
      const events = await listMyEvents();
      const boothGroups = await Promise.all(
        events.map((item) =>
          listVendorHallBooths(item.id).catch(() => [] as VendorHallBooth[]),
        ),
      );
      return boothGroups.flat();
    }
    if (canManageVendorInventory) return listMyVendorHallBooths();
    return [];
  }, [
    canCheckIn,
    canManageVendorInventory,
    event,
    staffScopedToAssignments,
    vendorScoped,
  ]);

  const load = useCallback(async () => {
    const [nextBooths, nextMapStatus] = await Promise.all([
      loadBooths(),
      canSeeLiveMap && event
        ? getVendorHallFloorMapStatus(event.id).catch(() => null)
        : Promise.resolve(null),
    ]);
    setBooths(nextBooths);
    setMapStatus(nextMapStatus);
    const nextSelected =
      nextBooths.find((booth) => booth.id === selectedBoothId) ??
      nextBooths[0] ??
      null;
    setSelectedBoothId(nextSelected?.id ?? null);
    if (nextSelected) {
      setItems(await listVendorHallInventory(nextSelected.id));
    } else {
      setItems([]);
    }
  }, [canSeeLiveMap, event, loadBooths, selectedBoothId]);

  useEffect(() => {
    let active = true;
    let objectUrl: string | null = null;
    setFloorMapUrl(null);
    if (!canSeeLiveMap || !event || !mapStatus?.floor_map?.has_image) return;
    void getVendorHallFloorMapContent(event.id, true)
      .then((blob) => {
        if (!active) return;
        objectUrl = URL.createObjectURL(blob);
        setFloorMapUrl(objectUrl);
      })
      .catch(() => undefined);
    return () => {
      active = false;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [
    canSeeLiveMap,
    event,
    mapStatus?.floor_map?.has_image,
    mapStatus?.floor_map?.uploaded_at,
  ]);

  useEffect(() => {
    let active = true;
    void load()
      .then(() => undefined)
      .catch((caught: unknown) => {
        if (active)
          setError(
            caught instanceof Error
              ? caught.message
              : "Unable to load the vendor hall.",
          );
      });
    return () => {
      active = false;
    };
  }, [load]);

  useEffect(() => {
    if (!selectedBoothId) return;
    let active = true;
    void listVendorHallInventory(selectedBoothId)
      .then((nextItems) => {
        if (active) setItems(nextItems);
      })
      .catch((caught: unknown) => {
        if (active)
          setError(
            caught instanceof Error
              ? caught.message
              : "Unable to load inventory.",
          );
      });
    return () => {
      active = false;
    };
  }, [selectedBoothId]);

  async function action(work: () => Promise<unknown>, success: string) {
    if (boothLocked) {
      setMessage("This booth is complete and locked for editing.");
      return;
    }
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      await work();
      await load();
      setMessage(success);
    } catch (caught) {
      setError(
        caught instanceof Error ? caught.message : "Vendor hall action failed",
      );
    } finally {
      setBusy(false);
    }
  }

  async function selectBooth(booth: VendorHallBooth) {
    setSelectedBoothId(booth.id);
    setValidatedItemIds(new Set());
    setOpenItemId(null);
    setError(null);
    try {
      setItems(await listVendorHallInventory(booth.id));
    } catch (caught) {
      setError(
        caught instanceof Error
          ? caught.message
          : "Unable to load the selected booth inventory.",
      );
    }
  }

  async function addItem(formEvent: FormEvent<HTMLFormElement>) {
    formEvent.preventDefault();
    if (!selectedBooth) return;
    const form = formEvent.currentTarget;
    await action(
      () =>
        createVendorHallInventoryItem(
          selectedBooth.id,
          itemPayload(new FormData(form)),
        ),
      "Inventory item added.",
    );
    form.reset();
  }

  async function importInventory(formEvent: FormEvent<HTMLFormElement>) {
    formEvent.preventDefault();
    if (!selectedBooth) return;
    const form = formEvent.currentTarget;
    const file = new FormData(form).get("file");
    if (!(file instanceof File) || !file.size) return;
    await action(
      () => importVendorHallInventory(selectedBooth.id, file),
      "Inventory import completed.",
    );
    form.reset();
  }

  async function uploadAttachment(
    item: VendorHallInventoryItem,
    formEvent: FormEvent<HTMLFormElement>,
  ) {
    formEvent.preventDefault();
    if (!selectedBooth) return;
    const form = formEvent.currentTarget;
    const data = new FormData(form);
    const file = data.get("file");
    const attachmentType = String(data.get("attachment_type")) as
      | "photo"
      | "spec_sheet"
      | "other";
    if (!(file instanceof File) || !file.size) return;
    await action(
      () =>
        uploadVendorHallItemAttachment(
          selectedBooth.id,
          item.id,
          attachmentType,
          file,
        ),
      "Attachment uploaded.",
    );
    form.reset();
  }

  async function downloadAttachment(
    item: VendorHallInventoryItem,
    attachment: VendorHallItemAttachment,
  ) {
    if (!selectedBooth) return;
    setBusy(true);
    setError(null);
    try {
      const { blob, filename } = await downloadVendorHallItemAttachment(
        selectedBooth.id,
        item.id,
        attachment.id,
      );
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = filename ?? attachment.filename;
      anchor.click();
      URL.revokeObjectURL(url);
    } catch (caught) {
      setError(
        caught instanceof Error
          ? caught.message
          : "Unable to download the attachment.",
      );
    } finally {
      setBusy(false);
    }
  }

  async function deleteAttachment(
    item: VendorHallInventoryItem,
    attachment: VendorHallItemAttachment,
  ) {
    if (!selectedBooth) return;
    await action(
      () =>
        deleteVendorHallItemAttachment(
          selectedBooth.id,
          item.id,
          attachment.id,
        ),
      "Attachment removed.",
    );
  }

  async function saveItem(
    item: VendorHallInventoryItem,
    formEvent: FormEvent<HTMLFormElement>,
  ) {
    formEvent.preventDefault();
    if (!selectedBooth) return;
    const data = new FormData(formEvent.currentTarget);
    const status = String(data.get("status")) as VendorHallItemStatus;
    const notes = String(data.get("notes") || "") || null;
    const condition =
      (String(data.get("condition") || "") as VendorHallItemCondition) || null;
    if (canCheckIn) {
      await action(
        () =>
          updateVendorHallInventoryItemStaff(selectedBooth.id, item.id, {
            quantity_checked_in: Number(data.get("quantity_checked")) || 0,
            condition: condition ?? "unknown",
            staff_notes: notes,
          }),
        "Inventory item saved.",
      );
      return;
    }
    await action(
      () =>
        updateVendorHallInventoryItem(selectedBooth.id, item.id, {
          item_name: item.item_name,
          model_number: item.model_number,
          serial_number: item.serial_number,
          description: item.description,
          quantity_expected: item.quantity_expected,
          unit_price: item.unit_price,
          currency: item.currency,
          condition: condition ?? item.condition,
          status,
          available_for_sale: item.available_for_sale,
          sell_to_buddys_price: item.sell_to_buddys_price,
          notes: item.notes,
          vendor_notes: notes,
        }),
      "Inventory item saved.",
    );
  }

  async function validateItem(item: VendorHallInventoryItem) {
    if (!selectedBooth) return;
    const form = document.getElementById(
      `vendor-hall-item-${item.id}`,
    ) as HTMLFormElement | null;
    const data = form ? new FormData(form) : null;
    const quantityValue = data?.get("quantity_checked");
    const quantityChecked =
      quantityValue === null || quantityValue === undefined
        ? item.quantity_checked_in
        : Number(quantityValue);
    const notes = String(data?.get("notes") || "") || item.staff_notes || null;
    await action(
      () =>
        checkinVendorHallInventoryItem(selectedBooth.id, item.id, {
          status: item.status,
          quantity_checked: quantityChecked,
          condition: item.condition,
          damage_notes: notes,
          exception_notes: notes,
          staff_notes: notes,
        }),
      "Inventory item validated.",
    );
    setValidatedItemIds((current) => new Set(current).add(item.id));
  }

  async function splitItem(item: VendorHallInventoryItem) {
    if (!selectedBooth || item.quantity_expected < 2) return;
    const value = window.prompt(
      `How many of the ${item.quantity_expected} units should be split into a separate damaged/removal entry?`,
      "1",
    );
    const quantity = Number(value);
    if (
      !Number.isInteger(quantity) ||
      quantity < 1 ||
      quantity >= item.quantity_expected
    ) {
      return;
    }
    await action(
      () =>
        splitVendorHallInventoryItem(selectedBooth.id, item.id, {
          split_quantity: quantity,
          status: "damaged",
          notes: "Split during vendor inventory review.",
        }),
      "Inventory quantity split into a separate exception entry.",
    );
  }

  if (!canManageVendorInventory && !canCheckIn) return null;
  if (!booths.length && compact) return null;

  return (
    <section
      id="assigned-vendor-hall-work"
      className={
        compact
          ? "event-ui event-vendor-hall-panel mb-6"
          : "event-ui rounded-2xl border bg-white p-5"
      }
    >
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="brand-eyebrow">Vendor hall</p>
          <h2 className={compact ? "" : "text-xl font-bold"}>
            {canCheckIn ? "Booth check-in" : "Booth inventory"}
          </h2>
          <p className={compact ? "" : "text-sm text-slate-600"}>
            {canCheckIn
              ? "Validate booth inventory, record exceptions, and complete setup."
              : "Add inventory, mark sale availability, and submit your booth for review."}
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
      <div className="mt-4 grid gap-4 lg:grid-cols-[280px_1fr]">
        <div className="event-vendor-hall-selector rounded-xl border p-3">
          <div className="flex items-center justify-between gap-2">
            <strong>Vendors and booths</strong>
            <span className="text-xs text-slate-400">
              {booths.length} total
            </span>
          </div>
          {!vendorScoped && !staffScopedToAssignments ? (
            <label className="mt-3 block text-xs font-bold uppercase tracking-wide text-slate-400">
              Find vendor or booth
              <input
                className="mt-1 w-full"
                onChange={(event) => searchBooths(event.target.value)}
                placeholder="Search by vendor, name, or booth number"
                type="search"
                value={boothSearch}
              />
            </label>
          ) : null}
          <div
            aria-label="Vendor booth search results"
            className="event-vendor-hall-search-results mt-3"
            role="listbox"
          >
            {!filteredBooths.length ? (
              <p className="rounded-lg border border-dashed p-3 text-sm text-slate-500">
                No matching booths
              </p>
            ) : (
              filteredBooths.map((booth) => (
                <button
                  aria-selected={selectedBooth?.id === booth.id}
                  className={
                    selectedBooth?.id === booth.id
                      ? "event-vendor-hall-search-result is-selected"
                      : "event-vendor-hall-search-result"
                  }
                  key={booth.id}
                  onClick={() => void selectBooth(booth)}
                  role="option"
                  type="button"
                >
                  <strong>{booth.vendor_name ?? booth.vendor_code}</strong>
                  <span>
                    {booth.booth_name} · Booth {booth.booth_number || "TBD"}
                  </span>
                  <small>{booth.status.replaceAll("_", " ")}</small>
                </button>
              ))
            )}
          </div>
          {selectedBooth ? (
            <div className="mt-3 rounded-lg border border-blue-400/20 bg-blue-950/30 p-3 text-sm">
              <strong>{selectedBooth.booth_name}</strong>
              <p className="text-slate-400">
                {selectedBooth.vendor_name ?? selectedBooth.vendor_code} · Booth{" "}
                {selectedBooth.booth_number || "TBD"}
              </p>
            </div>
          ) : null}
          {!booths.length ? (
            <p className="mt-3 rounded-xl border border-dashed p-4 text-sm text-slate-500">
              No vendor hall booths are assigned yet.
            </p>
          ) : null}
        </div>
        {selectedBooth ? (
          <div className="space-y-4">
            <div className="rounded-xl border bg-slate-50 p-4">
              <p className="brand-eyebrow">{selectedBooth.event_name}</p>
              <h3 className="text-lg font-bold">{selectedBooth.booth_name}</h3>
              <p className="text-sm text-slate-600">
                {items.length} inventory item{items.length === 1 ? "" : "s"} ·{" "}
                {selectedBooth.available_for_sale_count} marked for sale ·{" "}
                {selectedBooth.exceptions_count} exception
                {selectedBooth.exceptions_count === 1 ? "" : "s"}
              </p>
              {boothLocked ? (
                <p className="mt-2 rounded-lg border border-green-300/40 bg-green-50/10 p-2 text-sm text-green-200">
                  This booth is complete and locked for editing.
                </p>
              ) : null}
              <div className="mt-3 flex flex-wrap gap-2">
                {canManageVendorInventory ? (
                  <fieldset disabled={boothLocked} className="contents">
                    <button
                      className="brand-button"
                      disabled={busy || !items.length}
                      onClick={() =>
                        void action(
                          () => submitVendorHallInventory(selectedBooth.id),
                          "Booth inventory submitted.",
                        )
                      }
                      type="button"
                    >
                      Submit inventory
                    </button>
                    <button
                      className="brand-button brand-button-secondary"
                      disabled={busy || !items.length}
                      onClick={() =>
                        void action(
                          () =>
                            markVendorHallBoothReadyForInspection(
                              selectedBooth.id,
                            ),
                          "Booth marked ready for inspection.",
                        )
                      }
                      type="button"
                    >
                      Ready for inspection
                    </button>
                  </fieldset>
                ) : null}
                {canCheckIn ? (
                  <fieldset disabled={boothLocked} className="contents">
                    <button
                      className="brand-button"
                      disabled={busy}
                      onClick={() =>
                        void action(
                          () => startVendorHallBoothCheckin(selectedBooth.id),
                          "Booth check-in started.",
                        )
                      }
                      type="button"
                    >
                      {staffScopedToAssignments
                        ? "Start validation"
                        : "Start check-in"}
                    </button>
                    <button
                      className="brand-button brand-button-secondary"
                      // The API is the source of truth for validation completion.
                      // Keep this actionable so a refreshed/stale client cannot
                      // strand staff; the server still blocks incomplete booths.
                      disabled={busy}
                      onClick={() =>
                        void action(
                          () =>
                            completeVendorHallBoothCheckin(selectedBooth.id),
                          "Booth check-in completed.",
                        )
                      }
                      type="button"
                    >
                      Complete check-in
                    </button>
                  </fieldset>
                ) : null}
              </div>
            </div>
            {canManageVendorInventory ? (
              <fieldset disabled={boothLocked} className="contents">
                <div className="grid gap-4 xl:grid-cols-2">
                  <form
                    className="event-vendor-hall-form rounded-xl border p-4"
                    onSubmit={(formEvent) => void importInventory(formEvent)}
                  >
                    <h3 className="font-bold">Import inventory CSV or Excel</h3>
                    <p className="text-sm text-slate-600">
                      CSV and XLSX files can include item_name, model_number,
                      serial_number, quantity_expected, unit_price, condition,
                      available_for_sale, and sell_to_buddys_price.
                    </p>
                    <input
                      accept=".csv,.xlsx,.xlsm,text/csv,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                      name="file"
                      required
                      type="file"
                    />
                    <button className="brand-button" disabled={busy}>
                      Import inventory
                    </button>
                  </form>
                  <form
                    className="event-vendor-hall-form rounded-xl border p-4"
                    onSubmit={(formEvent) => void addItem(formEvent)}
                  >
                    <h3 className="font-bold">Add booth item</h3>
                    <div className="event-vendor-hall-fields">
                      <input
                        name="item_name"
                        placeholder="Item name"
                        required
                      />
                      <input name="model_number" placeholder="Model number" />
                      <input name="serial_number" placeholder="Serial number" />
                      <input
                        min={1}
                        name="quantity_expected"
                        placeholder="Qty"
                        type="number"
                        defaultValue={1}
                      />
                      <input
                        name="unit_price"
                        placeholder="Price"
                        type="number"
                      />
                      <select name="condition" defaultValue="unknown">
                        {conditions.map((condition) => (
                          <option key={condition} value={condition}>
                            {condition.replaceAll("_", " ")}
                          </option>
                        ))}
                      </select>
                    </div>
                    <textarea
                      name="description"
                      placeholder="Description / notes"
                    />
                    <label className="event-vendor-hall-sale-toggle text-sm font-bold">
                      <input name="available_for_sale" type="checkbox" />
                      <span>Available for sale to Buddy&apos;s</span>
                    </label>
                    <input
                      name="sell_to_buddys_price"
                      placeholder="Sell-to-Buddy's price"
                      type="number"
                    />
                    <button className="brand-button" disabled={busy}>
                      Add inventory item
                    </button>
                  </form>
                </div>
              </fieldset>
            ) : null}
            <div className="space-y-3">
              {items.map((item) => (
                <details
                  className="rounded-xl border p-4"
                  key={item.id}
                  open={openItemId === item.id}
                  onToggle={(event) => {
                    if (event.currentTarget.open) setOpenItemId(item.id);
                    else if (openItemId === item.id) setOpenItemId(null);
                  }}
                >
                  <summary
                    className="event-inventory-item-summary cursor-pointer list-none"
                    style={{
                      position: "relative",
                      display: "block",
                      minHeight: "3.25rem",
                      paddingRight: "6.5rem",
                    }}
                  >
                    <div>
                      <p className="brand-eyebrow">
                        {item.status.replaceAll("_", " ")}
                      </p>
                      <h3 className="font-bold">{item.item_name}</h3>
                      <p className="text-sm text-slate-600">
                        {item.model_number ?? "No model"} · Qty{" "}
                        {item.quantity_checked_in}/{item.quantity_expected} ·{" "}
                        {item.condition.replaceAll("_", " ")}
                      </p>
                    </div>
                    {item.available_for_sale ? (
                      <span
                        className="event-inventory-sale-badge h-fit rounded-full bg-green-50 px-3 py-1 text-xs font-bold text-green-800"
                        style={{
                          position: "absolute",
                          top: 0,
                          right: 0,
                          whiteSpace: "nowrap",
                        }}
                      >
                        For sale
                      </span>
                    ) : null}
                  </summary>
                  {item.attachments.length ? (
                    <div className="mt-3 flex flex-wrap gap-2">
                      {item.attachments.map((attachment) => (
                        <div className="contents" key={attachment.id}>
                          <button
                            className="brand-button brand-button-secondary"
                            disabled={busy}
                            onClick={() =>
                              void downloadAttachment(item, attachment)
                            }
                            type="button"
                          >
                            {attachment.attachment_type.replaceAll("_", " ")}:{" "}
                            {attachment.filename}
                          </button>
                          {canManageVendorInventory ? (
                            <button
                              className="brand-button brand-button-danger"
                              disabled={busy || boothLocked}
                              onClick={() =>
                                void deleteAttachment(item, attachment)
                              }
                              type="button"
                            >
                              Remove {attachment.filename}
                            </button>
                          ) : null}
                        </div>
                      ))}
                    </div>
                  ) : null}
                  {canCheckIn || canManageVendorInventory ? (
                    <>
                      <fieldset disabled={boothLocked} className="contents">
                        <form
                          id={`vendor-hall-item-${item.id}`}
                          className="event-vendor-hall-checkin mt-3"
                          onSubmit={(formEvent) =>
                            void saveItem(item, formEvent)
                          }
                        >
                          <select
                            disabled={staffScopedToAssignments}
                            name="status"
                            defaultValue={item.status}
                          >
                            {itemStatuses.map((status) => (
                              <option key={status} value={status}>
                                {status.replaceAll("_", " ")}
                              </option>
                            ))}
                          </select>
                          <input
                            min={0}
                            name="quantity_checked"
                            type="number"
                            defaultValue={
                              item.quantity_checked_in || item.quantity_expected
                            }
                          />
                          <select
                            disabled={staffScopedToAssignments}
                            name="condition"
                            defaultValue={item.condition}
                          >
                            {conditions.map((condition) => (
                              <option key={condition} value={condition}>
                                {condition.replaceAll("_", " ")}
                              </option>
                            ))}
                          </select>
                          <input
                            name="notes"
                            placeholder="Damage / exception notes"
                          />
                          <button className="brand-button" disabled={busy}>
                            Save inventory item
                          </button>
                          {staffScopedToAssignments ? (
                            <button
                              className="brand-button brand-button-secondary"
                              disabled={
                                busy ||
                                item.validated ||
                                validatedItemIds.has(item.id)
                              }
                              onClick={() => void validateItem(item)}
                              type="button"
                            >
                              {item.validated || validatedItemIds.has(item.id)
                                ? "Validated"
                                : "Validate"}
                            </button>
                          ) : null}
                          {canManageVendorInventory &&
                          item.quantity_expected > 1 ? (
                            <button
                              className="brand-button brand-button-secondary"
                              disabled={busy}
                              onClick={() => void splitItem(item)}
                              type="button"
                            >
                              Split damaged quantity
                            </button>
                          ) : null}
                        </form>
                        <form
                          className="event-vendor-hall-checkin mt-3"
                          onSubmit={(formEvent) =>
                            void uploadAttachment(item, formEvent)
                          }
                        >
                          <select name="attachment_type" defaultValue="photo">
                            <option value="photo">Photo</option>
                            <option value="spec_sheet">Spec sheet</option>
                            <option value="other">Other</option>
                          </select>
                          <input
                            accept="image/png,image/jpeg,image/webp,application/pdf"
                            name="file"
                            required
                            type="file"
                          />
                          <button className="brand-button" disabled={busy}>
                            Upload file
                          </button>
                        </form>
                      </fieldset>
                    </>
                  ) : null}
                </details>
              ))}
              {!items.length ? (
                <p className="rounded-xl border border-dashed p-5 text-sm text-slate-500">
                  No booth inventory has been added yet.
                </p>
              ) : null}
            </div>
          </div>
        ) : null}
      </div>
      {canSeeLiveMap ? (
        <section className="mt-6 rounded-2xl border bg-white p-4">
          <div className="mb-3">
            <p className="brand-eyebrow">Live navigation</p>
            <h3 className="text-lg font-bold">Vendor hall progress map</h3>
            <p className="text-sm text-slate-600">
              Use the map to see booth status and plan the shortest path between
              inspections. Staff see only their assigned booths; administrators
              see the complete hall.
            </p>
          </div>
          {visibleMapStatus ? (
            <VendorHallLiveMap
              mapStatus={visibleMapStatus}
              sourceUrl={floorMapUrl}
              hideDirectoryTools
              allowContactRepresentatives={false}
              offlineReadOnly
            />
          ) : (
            <p className="rounded-xl border border-dashed p-5 text-sm text-slate-500">
              The live floor map is not available for this event yet.
            </p>
          )}
        </section>
      ) : null}
    </section>
  );
}
