"use client";

import { FormEvent, useEffect, useState } from "react";
import {
  listAvailableEventVendors,
  listEventVendorBooths,
} from "@/lib/event-vendor-booth-api";
import { CatalogVendor } from "@/lib/purchasing-api";
import {
  addEventMembership,
  assignEventMembershipSubEvents,
  EventAccountDirectoryEntry,
  EventMembership,
  listEventAccountDirectory,
  ManagedEvent,
  updateEventMembershipVendors,
  updateEventMembershipLoadoutRole,
  updateEventMembershipRole,
} from "@/lib/event-admin-api";

type AttendeeCategory = EventMembership["membership_type"];

const attendeeCategories: Array<{ value: AttendeeCategory; label: string }> = [
  { value: "staff", label: "Staff" },
  { value: "team_lead", label: "Team lead" },
  { value: "dockmaster", label: "Dockmaster" },
  { value: "overseer", label: "Loadout overseer" },
  { value: "vendor", label: "Vendor representative" },
  { value: "franchise_representative", label: "Franchise representative" },
  { value: "executive", label: "Executive" },
  { value: "admin", label: "Admin" },
];

const loadoutRoleOptions = [
  { value: "", label: "No loadout role" },
  { value: "team_lead", label: "Team lead" },
  { value: "dockmaster", label: "Dockmaster" },
  { value: "overseer", label: "Loadout overseer" },
] as const;

export function EventAttendeeManagementPanel({
  event,
  onUpdated,
}: {
  event: ManagedEvent;
  onUpdated: (eventId: string) => Promise<void>;
}) {
  const [category, setCategory] = useState<AttendeeCategory>("staff");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [directory, setDirectory] = useState<EventAccountDirectoryEntry[]>([]);
  const [selectedAccount, setSelectedAccount] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [email, setEmail] = useState("");
  const [vendorCompanies, setVendorCompanies] = useState<CatalogVendor[]>([]);
  const [selectedVendors, setSelectedVendors] = useState<string[]>([]);
  const [accountVendorCodes, setAccountVendorCodes] = useState<string[]>([]);
  const [registeredVendorCodes, setRegisteredVendorCodes] = useState<string[]>(
    [],
  );
  const [expandedMemberId, setExpandedMemberId] = useState<string | null>(null);

  // Keep the picker tied to the account directory as its source of truth.  Do
  // not fall back to the event-wide vendor list: that would let a
  // representative select a vendor they do not represent in the main portal.
  const selectedAccountVendorCodes = new Set(
    (
      directory.find((user) => String(user.id) === selectedAccount)
        ?.vendor_codes ?? accountVendorCodes
    ).map((code) => code.trim().toUpperCase()),
  );
  const registeredCodes = new Set(
    registeredVendorCodes.map((code) => code.trim().toUpperCase()),
  );

  useEffect(() => {
    void listEventAccountDirectory()
      .then((users) => setDirectory(users.filter((user) => user.is_active)))
      .catch(() => setDirectory([]));
  }, []);

  useEffect(() => {
    void Promise.all([
      listAvailableEventVendors(event.id),
      listEventVendorBooths(event.id),
    ])
      .then(([vendors, booths]) => {
        setVendorCompanies(vendors);
        setRegisteredVendorCodes([
          ...new Set(booths.map((booth) => booth.vendor_code)),
        ]);
      })
      .catch(() => {
        setVendorCompanies([]);
        setRegisteredVendorCodes([]);
      });
  }, [event.id]);

  async function add(eventForm: FormEvent<HTMLFormElement>) {
    eventForm.preventDefault();
    const form = eventForm.currentTarget;
    const data = new FormData(form);
    setBusy(true);
    setMessage(null);
    setError(null);
    try {
      await addEventMembership(event.id, {
        email: String(data.get("email")),
        display_name: String(data.get("display_name")),
        password: String(data.get("password") || "") || null,
        membership_type: category,
        vendor_code:
          category === "vendor" ? (selectedVendors[0] ?? null) : null,
        vendor_codes: category === "vendor" ? selectedVendors : [],
        entity_code:
          category === "franchise_representative"
            ? String(data.get("entity_code")).trim().toUpperCase()
            : null,
        module_codes: [],
        task_scope: String(data.get("task_scope") || "") || null,
        is_active: true,
      });
      form.reset();
      setSelectedAccount("");
      setDisplayName("");
      setEmail("");
      setCategory("staff");
      setSelectedVendors([]);
      await onUpdated(event.id);
      setMessage("Attendee linked to this event.");
    } catch (caught) {
      setError(
        caught instanceof Error
          ? caught.message
          : "Unable to add the attendee.",
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="event-ui rounded-2xl border bg-white p-5">
      <p className="brand-eyebrow">Event administration</p>
      <h3 className="text-xl font-bold">Attendees and event accounts</h3>
      <p className="mt-1 text-sm text-slate-600">
        Enter an existing account email to link it, or supply a password to
        create a new account.
      </p>
      {message ? (
        <p className="mt-3 rounded-lg bg-green-50 p-3 text-green-800">
          {message}
        </p>
      ) : null}
      {error ? (
        <p className="mt-3 rounded-lg bg-red-50 p-3 text-red-800">{error}</p>
      ) : null}
      <div className="mt-4 grid gap-5 lg:grid-cols-[1fr_1fr]">
        <div className="max-h-96 space-y-2 overflow-auto">
          {event.memberships.map((member) => (
            <article className="rounded-xl border p-3" key={member.id}>
              <button
                aria-expanded={expandedMemberId === member.id}
                className="flex w-full items-start justify-between gap-3 text-left"
                onClick={() =>
                  setExpandedMemberId((current) =>
                    current === member.id ? null : member.id,
                  )
                }
                type="button"
              >
                <span>
                  <strong>{member.display_name}</strong>
                  <span className="block text-sm text-slate-600">
                    {member.email}
                  </span>
                  <span className="mt-1 block text-xs font-bold uppercase text-blue-700">
                    {member.membership_type.replaceAll("_", " ")}
                  </span>
                </span>
                <span aria-hidden="true" className="text-lg leading-none">
                  {expandedMemberId === member.id ? "−" : "+"}
                </span>
              </button>
              {expandedMemberId === member.id ? (
                <>
                  {member.entity_code ? (
                    <p className="mt-2 text-xs">Entity {member.entity_code}</p>
                  ) : null}
                  <label className="mt-3 block text-sm font-semibold">
                    Event role
                    <select
                      className="mt-1 w-full rounded-lg border bg-white p-2"
                      defaultValue={member.membership_type}
                      onChange={(input) => {
                        void updateEventMembershipRole(
                          event.id,
                          member.id,
                          input.currentTarget.value as AttendeeCategory,
                        ).then(() => onUpdated(event.id));
                      }}
                    >
                      {attendeeCategories.map((item) => (
                        <option key={item.value} value={item.value}>
                          {item.label}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label className="mt-3 block text-sm font-semibold">
                    Loadout role (this event only)
                    <select
                      className="mt-1 w-full rounded-lg border bg-white p-2"
                      defaultValue={member.loadout_role ?? ""}
                      onChange={(input) => {
                        void updateEventMembershipLoadoutRole(
                          event.id,
                          member.id,
                          input.currentTarget.value === ""
                            ? null
                            : (input.currentTarget
                                .value as EventMembership["loadout_role"]),
                        ).then(() => onUpdated(event.id));
                      }}
                    >
                      {loadoutRoleOptions.map((item) => (
                        <option key={item.value} value={item.value}>
                          {item.label}
                        </option>
                      ))}
                    </select>
                    <span className="mt-1 block text-xs font-normal text-slate-500">
                      Applies only when this attendee opens the Store Loadout
                      sub-event.
                    </span>
                  </label>
                  {member.vendor_codes.length ? (
                    <p className="text-xs">
                      Vendors {member.vendor_codes.join(", ")}
                    </p>
                  ) : member.vendor_code ? (
                    <p className="text-xs">Vendor {member.vendor_code}</p>
                  ) : null}
                  {member.membership_type === "vendor" ? (
                    <VendorRegistrationEditor
                      event={event}
                      member={member}
                      vendorCompanies={vendorCompanies}
                      registeredVendorCodes={registeredVendorCodes}
                      accountVendorCodes={
                        directory.find(
                          (account) => account.id === member.user_id,
                        )?.vendor_codes ?? []
                      }
                      onUpdated={onUpdated}
                    />
                  ) : null}
                  <SubEventAssignments
                    event={event}
                    member={member}
                    onUpdated={onUpdated}
                  />
                </>
              ) : null}
            </article>
          ))}
          {!event.memberships.length ? (
            <p className="rounded-xl border border-dashed p-4 text-slate-500">
              No attendees added yet.
            </p>
          ) : null}
        </div>
        <form className="grid gap-3 rounded-xl bg-slate-50 p-4" onSubmit={add}>
          {directory.length ? (
            <label className="text-sm font-semibold">
              Add an existing account
              <select
                className="mt-1 w-full rounded-lg border bg-white p-3"
                onChange={(input) => {
                  const account = directory.find(
                    (user) => String(user.id) === input.target.value,
                  );
                  setSelectedAccount(input.target.value);
                  if (account) {
                    setDisplayName(account.display_name);
                    setEmail(account.email);
                    setAccountVendorCodes(
                      (account.vendor_codes ?? []).map((code) =>
                        code.trim().toUpperCase(),
                      ),
                    );
                    setSelectedVendors([]);
                  }
                }}
                value={selectedAccount}
              >
                <option value="">Select staff or another platform user</option>
                {directory.map((user) => (
                  <option key={user.id} value={user.id}>
                    {user.display_name} · {user.email}
                  </option>
                ))}
              </select>
            </label>
          ) : null}
          <input
            className="rounded-lg border bg-white p-3"
            name="display_name"
            onChange={(input) => setDisplayName(input.target.value)}
            placeholder="Display name"
            required
            value={displayName}
          />
          <input
            className="rounded-lg border bg-white p-3"
            name="email"
            onChange={(input) => setEmail(input.target.value)}
            placeholder="Account email"
            required
            type="email"
            value={email}
          />
          <input
            className="rounded-lg border bg-white p-3"
            minLength={12}
            name="password"
            placeholder="Password only for a new account"
            type="password"
          />
          <label className="text-sm font-semibold">
            Attendee category
            <select
              className="mt-1 w-full rounded-lg border bg-white p-3"
              name="membership_type"
              onChange={(input) =>
                setCategory(input.target.value as AttendeeCategory)
              }
              value={category}
            >
              {attendeeCategories.map((item) => (
                <option key={item.value} value={item.value}>
                  {item.label}
                </option>
              ))}
            </select>
          </label>
          {category === "vendor" ? (
            <label className="text-sm font-semibold">
              Vendor company
              <div className="mt-1 grid max-h-40 gap-2 overflow-auto rounded-lg border bg-white p-3">
                {vendorCompanies
                  .filter(
                    (vendor) =>
                      Boolean(selectedAccount) &&
                      selectedAccountVendorCodes.has(
                        vendor.vendor_code.trim().toUpperCase(),
                      ) &&
                      registeredCodes.has(
                        vendor.vendor_code.trim().toUpperCase(),
                      ),
                  )
                  .map((vendor) => (
                    <label
                      className="flex items-center gap-2"
                      key={vendor.vendor_code}
                    >
                      <input
                        checked={selectedVendors.includes(vendor.vendor_code)}
                        onChange={(input) =>
                          setSelectedVendors((current) =>
                            input.target.checked
                              ? [...current, vendor.vendor_code]
                              : current.filter(
                                  (code) => code !== vendor.vendor_code,
                                ),
                          )
                        }
                        type="checkbox"
                      />
                      <span>
                        {vendor.name}
                        {vendor.is_active ? "" : " (event only)"}
                      </span>
                    </label>
                  ))}
              </div>
              {!selectedAccount ? (
                <span className="mt-1 block text-xs font-normal text-amber-700">
                  Select an existing main-portal vendor representative first.
                </span>
              ) : null}
              {selectedAccount &&
              vendorCompanies.filter(
                (vendor) =>
                  selectedAccountVendorCodes.has(
                    vendor.vendor_code.trim().toUpperCase(),
                  ) &&
                  registeredCodes.has(vendor.vendor_code.trim().toUpperCase()),
              ).length === 0 ? (
                <span className="mt-1 block text-xs font-normal text-amber-700">
                  This account has no vendors registered for this event.
                </span>
              ) : null}
              <input
                name="vendor_code"
                type="hidden"
                value={selectedVendors[0] ?? ""}
              />
              <span className="mt-1 block text-xs font-normal text-slate-500">
                Select every vendor account this attendee may represent during
                this event.
              </span>
            </label>
          ) : null}
          {category === "franchise_representative" ? (
            <input
              className="rounded-lg border bg-white p-3"
              name="entity_code"
              placeholder="Ordering entity code"
              required
            />
          ) : null}
          <textarea
            className="rounded-lg border bg-white p-3"
            name="task_scope"
            placeholder="Event role, task scope, or notes"
          />
          <button
            className="rounded-xl bg-blue-800 p-3 font-bold text-white disabled:bg-slate-400"
            disabled={busy}
          >
            {busy ? "Adding…" : "Add attendee"}
          </button>
        </form>
      </div>
    </section>
  );
}

function VendorRegistrationEditor({
  event,
  member,
  vendorCompanies,
  registeredVendorCodes,
  accountVendorCodes,
  onUpdated,
}: {
  event: ManagedEvent;
  member: EventMembership;
  vendorCompanies: CatalogVendor[];
  registeredVendorCodes: string[];
  accountVendorCodes: string[];
  onUpdated: (eventId: string) => Promise<void>;
}) {
  const [selected, setSelected] = useState<string[]>(member.vendor_codes);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const owned = new Set(accountVendorCodes.map((code) => code.toUpperCase()));
  const registered = new Set(
    registeredVendorCodes.map((code) => code.toUpperCase()),
  );
  const options = vendorCompanies.filter((vendor) => {
    const code = vendor.vendor_code.toUpperCase();
    if (registered.has(code) && owned.has(code)) return true;
    if (!registered.has(code)) return false;
    const vendorName = vendor.name.toUpperCase().replace(/[^A-Z0-9]/g, "");
    return vendorCompanies.some(
      (ownedVendor) =>
        owned.has(ownedVendor.vendor_code.toUpperCase()) &&
        (() => {
          const ownedName = ownedVendor.name
            .toUpperCase()
            .replace(/[^A-Z0-9]/g, "");
          return (
            ownedName === vendorName ||
            ownedName.includes(vendorName) ||
            vendorName.includes(ownedName)
          );
        })(),
    );
  });

  useEffect(() => setSelected(member.vendor_codes), [member.vendor_codes]);

  return (
    <div className="mt-3 border-t pt-3">
      <p className="text-xs font-bold uppercase text-slate-500">
        Registered vendor access
      </p>
      <p className="mt-1 text-xs text-slate-500">
        Add or remove vendors this attendee may represent. Only the attendee’s
        main-portal vendor assignments that have a booth in this event appear.
      </p>
      <div className="mt-2 grid gap-1">
        {options.map((vendor) => (
          <label
            className={`event-selectable flex items-center gap-2 rounded-lg border px-2 py-1 text-xs ${selected.includes(vendor.vendor_code) ? "is-selected" : ""}`}
            key={vendor.vendor_code}
          >
            <input
              checked={selected.includes(vendor.vendor_code)}
              onChange={(input) =>
                setSelected((current) =>
                  input.target.checked
                    ? [...current, vendor.vendor_code]
                    : current.filter((code) => code !== vendor.vendor_code),
                )
              }
              type="checkbox"
            />
            {vendor.name}
          </label>
        ))}
      </div>
      {error ? <p className="mt-2 text-xs text-red-700">{error}</p> : null}
      <button
        className="mt-2 rounded-lg border px-3 py-1 text-xs font-bold disabled:text-slate-400"
        disabled={busy || !selected.length}
        onClick={() => {
          setBusy(true);
          setError(null);
          void updateEventMembershipVendors(event.id, member.id, selected)
            .then(() => onUpdated(event.id))
            .catch((caught: unknown) =>
              setError(
                caught instanceof Error
                  ? caught.message
                  : "Unable to update vendor access.",
              ),
            )
            .finally(() => setBusy(false));
        }}
        type="button"
      >
        {busy ? "Saving…" : "Save vendor access"}
      </button>
    </div>
  );
}

function SubEventAssignments({
  event,
  member,
  onUpdated,
}: {
  event: ManagedEvent;
  member: EventMembership;
  onUpdated: (eventId: string) => Promise<void>;
}) {
  const initial = member.sub_event_scope_configured
    ? member.sub_event_ids
    : event.sub_events.map((item) => item.id);
  const [selected, setSelected] = useState<string[]>(initial);
  const [roles, setRoles] = useState(member.sub_event_roles);
  const [busy, setBusy] = useState(false);

  return (
    <div className="mt-3 border-t pt-3">
      <p className="text-xs font-bold uppercase text-slate-500">
        Sub-event access
      </p>
      <div className="mt-2 space-y-1">
        {event.sub_events.map((subEvent) => (
          <label
            className={`event-selectable flex items-center gap-2 rounded-lg border px-2 py-1 text-xs ${selected.includes(subEvent.id) ? "is-selected" : ""}`}
            key={subEvent.id}
          >
            <input
              checked={selected.includes(subEvent.id)}
              onChange={() =>
                setSelected((current) =>
                  current.includes(subEvent.id)
                    ? current.filter((id) => id !== subEvent.id)
                    : [...current, subEvent.id],
                )
              }
              type="checkbox"
            />
            {subEvent.name}
            {selected.includes(subEvent.id) ? (
              <select
                className="ml-auto rounded border bg-white px-1 py-1 text-xs"
                value={roles[subEvent.id] ?? ""}
                onChange={(input) =>
                  setRoles((current) => ({
                    ...current,
                    [subEvent.id]: (input.currentTarget.value ||
                      null) as EventMembership["loadout_role"],
                  }))
                }
              >
                <option value="">Standard event role</option>
                <option value="team_lead">Team lead</option>
                <option value="dockmaster">Dockmaster</option>
                <option value="overseer">Loadout overseer</option>
              </select>
            ) : null}
          </label>
        ))}
      </div>
      <button
        className="mt-2 rounded-lg border px-3 py-1 text-xs font-bold disabled:text-slate-400"
        disabled={busy}
        onClick={() => {
          setBusy(true);
          void assignEventMembershipSubEvents(
            event.id,
            member.id,
            selected,
            Object.fromEntries(
              selected.map((subEventId) => [
                subEventId,
                roles[subEventId] ?? null,
              ]),
            ),
          )
            .then(() => onUpdated(event.id))
            .finally(() => setBusy(false));
        }}
        type="button"
      >
        {busy ? "Saving…" : "Save sub-event access"}
      </button>
    </div>
  );
}
