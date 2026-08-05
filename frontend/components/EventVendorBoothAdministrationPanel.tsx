"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
import { ManagedEvent } from "@/lib/event-admin-api";
import {
  createEventVendorBooth,
  createEventOnlyVendor,
  EventVendorBooth,
  EventVendorBoothStatus,
  EventVendorBoothWrite,
  listEventVendorBooths,
  listAvailableEventVendors,
  updateEventVendorBooth,
} from "@/lib/event-vendor-booth-api";
import { CatalogVendor } from "@/lib/purchasing-api";

const statuses: EventVendorBoothStatus[] = ["draft", "published"];

function writeFromForm(data: FormData): EventVendorBoothWrite {
  return {
    vendor_code: String(data.get("vendor_code")),
    booth_name: String(data.get("booth_name")),
    booth_number: String(data.get("booth_number") || "") || null,
    location: String(data.get("location") || "") || null,
    description: String(data.get("description") || "") || null,
    contact_name: String(data.get("contact_name") || "") || null,
    contact_email: String(data.get("contact_email") || "") || null,
    website_url: String(data.get("website_url") || "") || null,
    status: String(data.get("status")) as EventVendorBoothStatus,
  };
}

export function EventVendorBoothAdministrationPanel({
  event,
}: {
  event: ManagedEvent;
}) {
  const [booths, setBooths] = useState<EventVendorBooth[]>([]);
  const [editing, setEditing] = useState<EventVendorBooth | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [vendors, setVendors] = useState<CatalogVendor[]>([]);
  const [showAddVendor, setShowAddVendor] = useState(false);
  const [newVendorName, setNewVendorName] = useState("");
  const load = useCallback(
    () =>
      Promise.all([
        listEventVendorBooths(event.id).then(setBooths),
        listAvailableEventVendors(event.id).then(setVendors),
      ]).then(() => undefined),
    [event.id],
  );

  useEffect(() => {
    setEditing(null);
    void load();
  }, [load]);

  async function save(formEvent: FormEvent<HTMLFormElement>) {
    formEvent.preventDefault();
    const form = formEvent.currentTarget;
    setBusy(true);
    setError(null);
    try {
      const payload = writeFromForm(new FormData(form));
      if (editing) {
        await updateEventVendorBooth(event.id, editing.id, payload);
      } else {
        await createEventVendorBooth(event.id, payload);
      }
      form.reset();
      setEditing(null);
      await load();
    } catch (caught) {
      setError(
        caught instanceof Error
          ? caught.message
          : "Unable to save the vendor booth.",
      );
    } finally {
      setBusy(false);
    }
  }

  async function addEventVendor() {
    if (!newVendorName.trim()) return;
    setBusy(true);
    setError(null);
    try {
      const vendor = await createEventOnlyVendor(
        event.id,
        newVendorName.trim(),
      );
      setVendors((current) =>
        [...current, vendor].sort((a, b) => a.name.localeCompare(b.name)),
      );
      setNewVendorName("");
      setShowAddVendor(false);
    } catch (caught) {
      setError(
        caught instanceof Error
          ? caught.message
          : "Unable to add the event-only vendor.",
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="event-ui rounded-2xl border bg-white p-5">
      <p className="brand-eyebrow">Vendor event presence</p>
      <h3 className="text-xl font-bold">Vendor booths</h3>
      <p className="mt-1 text-sm text-slate-600">
        Create event-facing booth profiles for vendors tied to this show.
        Vendors can update the profile assigned to their account.
      </p>
      {error ? (
        <p className="mt-3 rounded-lg bg-red-50 p-3 text-red-800">{error}</p>
      ) : null}
      <div className="mt-4 grid gap-5 lg:grid-cols-2">
        <form
          className="grid gap-3 rounded-xl bg-slate-50 p-4"
          key={editing?.id ?? "new-vendor-booth"}
          onSubmit={save}
        >
          <label className="font-semibold">
            <span className="flex items-center justify-between gap-3">
              Vendor
              {!editing ? (
                <button
                  className="text-sm font-bold text-blue-700"
                  onClick={() => setShowAddVendor((value) => !value)}
                  type="button"
                >
                  + Add event-only vendor
                </button>
              ) : null}
            </span>
            <select
              className="mt-1 w-full rounded-lg border bg-white p-3"
              defaultValue={editing?.vendor_code ?? ""}
              disabled={Boolean(editing)}
              name="vendor_code"
              required
            >
              <option value="">Select vendor</option>
              {vendors.map((vendor) => (
                <option key={vendor.vendor_code} value={vendor.vendor_code}>
                  {vendor.name}
                  {vendor.is_active ? "" : " (event only)"}
                </option>
              ))}
            </select>
          </label>
          {showAddVendor && !editing ? (
            <div className="grid gap-2 rounded-xl border border-blue-200 bg-blue-50 p-3 sm:grid-cols-[1fr_auto]">
              <input
                className="rounded-lg border bg-white p-3"
                onChange={(input) => setNewVendorName(input.target.value)}
                placeholder="Service vendor name"
                value={newVendorName}
              />
              <button
                className="rounded-lg bg-blue-800 px-4 font-bold text-white disabled:bg-slate-400"
                disabled={busy || !newVendorName.trim()}
                onClick={() => void addEventVendor()}
                type="button"
              >
                Add vendor
              </button>
              <p className="text-xs text-slate-600 sm:col-span-2">
                Event-only vendors can have a booth but will not appear in
                purchasing or product ordering.
              </p>
            </div>
          ) : null}
          {editing ? (
            <input
              name="vendor_code"
              type="hidden"
              value={editing.vendor_code}
            />
          ) : null}
          <div className="grid gap-3 sm:grid-cols-2">
            <input
              className="rounded-lg border bg-white p-3"
              defaultValue={editing?.booth_name}
              name="booth_name"
              placeholder="Booth profile name"
              required
            />
            <input
              className="rounded-lg border bg-white p-3"
              defaultValue={editing?.booth_number ?? ""}
              name="booth_number"
              placeholder="Booth number"
            />
          </div>
          <input
            className="rounded-lg border bg-white p-3"
            defaultValue={editing?.location ?? ""}
            name="location"
            placeholder="Floor / hall / area"
          />
          <textarea
            className="rounded-lg border bg-white p-3"
            defaultValue={editing?.description ?? ""}
            name="description"
            placeholder="Short public booth description"
          />
          <div className="grid gap-3 sm:grid-cols-2">
            <input
              className="rounded-lg border bg-white p-3"
              defaultValue={editing?.contact_name ?? ""}
              name="contact_name"
              placeholder="Event contact"
            />
            <input
              className="rounded-lg border bg-white p-3"
              defaultValue={editing?.contact_email ?? ""}
              name="contact_email"
              placeholder="Contact email"
              type="email"
            />
          </div>
          <div className="grid gap-3 sm:grid-cols-2">
            <input
              className="rounded-lg border bg-white p-3"
              defaultValue={editing?.website_url ?? ""}
              name="website_url"
              placeholder="Website URL"
              type="url"
            />
            <select
              className="rounded-lg border bg-white p-3"
              defaultValue={editing?.status ?? "draft"}
              name="status"
            >
              {statuses.map((status) => (
                <option key={status} value={status}>
                  {status}
                </option>
              ))}
            </select>
          </div>
          <button
            className="rounded-xl bg-blue-800 p-3 font-bold text-white disabled:bg-slate-400"
            disabled={busy || !vendors.length}
          >
            {busy ? "Saving…" : editing ? "Save booth" : "Create vendor booth"}
          </button>
          {editing ? (
            <button
              className="rounded-xl border p-3 font-bold"
              onClick={() => setEditing(null)}
              type="button"
            >
              Cancel editing
            </button>
          ) : null}
          {!vendors.length ? (
            <p className="text-sm text-slate-500">
              No vendors are available. Add an event-only services vendor above.
            </p>
          ) : null}
        </form>
        <div className="max-h-[34rem] space-y-3 overflow-auto">
          {booths.map((booth) => (
            <article className="rounded-xl border p-4" key={booth.id}>
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <span className="text-xs font-bold uppercase text-blue-700">
                    {booth.status} · {booth.vendor_code}
                  </span>
                  <h4 className="font-bold">{booth.booth_name}</h4>
                  <p className="text-sm text-slate-600">
                    {booth.booth_number ?? "No booth #"} ·{" "}
                    {booth.location ?? "Location TBD"}
                  </p>
                </div>
                <button
                  className="text-sm font-bold text-blue-700"
                  onClick={() => setEditing(booth)}
                  type="button"
                >
                  Edit
                </button>
              </div>
              {booth.description ? (
                <p className="mt-2 text-sm text-slate-600">
                  {booth.description}
                </p>
              ) : null}
              <p className="mt-2 text-xs text-slate-500">
                {booth.contact_name ?? "No contact"} ·{" "}
                {booth.contact_email ?? "No email"}
              </p>
              <div className="mt-3 border-t pt-3">
                <p className="text-xs font-bold uppercase text-slate-500">
                  Linked vendor attendees
                </p>
                {event.memberships.filter(
                  (member) =>
                    member.membership_type === "vendor" &&
                    member.vendor_code === booth.vendor_code,
                ).length ? (
                  <ul className="mt-1 space-y-1 text-sm text-slate-700">
                    {event.memberships
                      .filter(
                        (member) =>
                          member.membership_type === "vendor" &&
                          member.vendor_code === booth.vendor_code,
                      )
                      .map((member) => (
                        <li key={member.id}>
                          {member.display_name} · {member.email}
                        </li>
                      ))}
                  </ul>
                ) : (
                  <p className="mt-1 text-sm text-slate-500">
                    No attendee accounts linked yet.
                  </p>
                )}
              </div>
            </article>
          ))}
          {!booths.length ? (
            <p className="rounded-xl border border-dashed p-5 text-slate-500">
              No vendor booths yet.
            </p>
          ) : null}
        </div>
      </div>
    </section>
  );
}
