"use client";

import { FormEvent, useEffect, useState } from "react";
import { useEventBranding } from "@/components/EventBrandingProvider";
import { useEventScope } from "@/components/EventScopeProvider";
import { EventVendorHallDirectory } from "@/components/EventVendorHallDirectory";
import { useAuth } from "@/lib/auth";
import {
  checkinStoreLoadoutItem,
  listMyStoreLoadoutAssignments,
  completeStoreLoadoutFinalReview,
  signStoreLoadoutAssignment,
  uploadStoreLoadoutItemEvidence,
  StoreLoadoutAssignment,
  StoreLoadoutItem,
  StoreLoadoutItemStatus,
} from "@/lib/store-loadout-api";

const checkinStatuses: StoreLoadoutItemStatus[] = [
  "found",
  "damaged",
  "missing",
  "substituted",
  "removed",
];

function statusLabel(status: string) {
  return status.replaceAll("_", " ");
}

function timeLabel(value: string | null) {
  if (!value) return "Not scheduled";
  return new Date(value).toLocaleString([], {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

export function StoreLoadoutLanding() {
  const { user } = useAuth();
  const { brandedClassName, brandedStyle } = useEventBranding();
  const eventId = useEventScope();
  const [assignments, setAssignments] = useState<StoreLoadoutAssignment[]>([]);
  const [selectedAssignmentId, setSelectedAssignmentId] = useState<
    string | null
  >(null);
  const [selectedItemId, setSelectedItemId] = useState<string | null>(null);
  const [busyKey, setBusyKey] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    const refresh = () =>
      void listMyStoreLoadoutAssignments()
        .then((items) => {
          if (active) {
            const scoped = eventId
              ? items.filter((item) => item.event_id === eventId)
              : items;
            setAssignments(scoped);
            setSelectedAssignmentId(
              (current) => current ?? scoped[0]?.id ?? null,
            );
            setSelectedItemId(
              (current) => current ?? scoped[0]?.items[0]?.id ?? null,
            );
          }
        })
        .catch(() => undefined);
    refresh();
    const timer = window.setInterval(refresh, 60_000);
    return () => {
      active = false;
      window.clearInterval(timer);
    };
  }, [eventId]);

  function replaceAssignment(next: StoreLoadoutAssignment) {
    setAssignments((current) =>
      current.map((assignment) =>
        assignment.id === next.id ? next : assignment,
      ),
    );
  }

  const selectedAssignment =
    assignments.find((item) => item.id === selectedAssignmentId) ?? null;
  const selectedItem =
    selectedAssignment?.items.find((item) => item.id === selectedItemId) ??
    null;

  async function submitCheckin(
    assignment: StoreLoadoutAssignment,
    item: StoreLoadoutItem,
    event: FormEvent<HTMLFormElement>,
  ) {
    event.preventDefault();
    // React may clear the synthetic event after the async request resolves;
    // retain the native form reference before awaiting the API call.
    const formElement = event.currentTarget;
    const form = new FormData(formElement);
    const key = `${assignment.id}-${item.id}`;
    setBusyKey(key);
    setMessage(null);
    try {
      const updated = await checkinStoreLoadoutItem(assignment.id, item.id, {
        status: String(form.get("status")) as StoreLoadoutItemStatus,
        quantity_found: Number(form.get("quantity_found")) || 0,
        damage_notes: String(form.get("damage_notes") || "") || null,
        missing_notes: String(form.get("missing_notes") || "") || null,
      });
      replaceAssignment(updated);
      setMessage("Item check-in saved.");
    } finally {
      setBusyKey(null);
    }
  }

  async function completeStore(assignment: StoreLoadoutAssignment) {
    setBusyKey(assignment.id);
    setMessage(null);
    try {
      const updated = await completeStoreLoadoutFinalReview(assignment.id, {
        notes:
          "Team lead verified the store inventory against the printed packing list.",
      });
      replaceAssignment(updated);
      setMessage("Store completed and team progress updated.");
    } finally {
      setBusyKey(null);
    }
  }

  async function uploadEvidence(
    assignment: StoreLoadoutAssignment,
    item: StoreLoadoutItem,
    event: FormEvent<HTMLFormElement>,
  ) {
    event.preventDefault();
    const form = event.currentTarget;
    const file = (form.elements.namedItem("evidence") as HTMLInputElement)
      ?.files?.[0];
    if (!file) return;
    setBusyKey(`${assignment.id}-${item.id}-evidence`);
    setMessage(null);
    try {
      await uploadStoreLoadoutItemEvidence(assignment.id, item.id, file);
      form.reset();
      setMessage("Photo evidence uploaded.");
    } finally {
      setBusyKey(null);
    }
  }

  async function signAssignment(
    assignment: StoreLoadoutAssignment,
    event: FormEvent<HTMLFormElement>,
  ) {
    event.preventDefault();
    const formElement = event.currentTarget;
    const form = new FormData(formElement);
    setBusyKey(`${assignment.id}-sign`);
    setMessage(null);
    try {
      const updated = await signStoreLoadoutAssignment(assignment.id, {
        signer_name:
          String(form.get("signer_name") || "") ||
          user?.display_name ||
          "Store staff",
        signer_email:
          String(form.get("signer_email") || "") ||
          user?.email ||
          "store@example.com",
        signature_text: String(form.get("signature_text") || ""),
        exception_summary: String(form.get("exception_summary") || "") || null,
      });
      replaceAssignment(updated);
      setMessage("Packing list signed.");
      formElement.reset();
    } finally {
      setBusyKey(null);
    }
  }

  if (!assignments.length) return null;

  return (
    <section
      className="event-ui store-loadout-panel mb-6"
      id="assigned-loadout-work"
    >
      <div>
        <p className="brand-eyebrow">Store loadout</p>
        <h2>Your pickup checklist</h2>
        <p>
          Confirm assigned booths and products before final packing-list review.
        </p>
      </div>
      {message ? <p className="store-loadout-message">{message}</p> : null}
      <div className="grid gap-4 lg:grid-cols-[minmax(15rem,0.8fr)_minmax(0,1.8fr)]">
        <div className="store-loadout-list max-h-[70vh] overflow-y-auto">
          {assignments.map((assignment) => (
            <article
              className={brandedClassName(
                assignment.event_id,
                "store-loadout-card",
              )}
              key={assignment.id}
              style={brandedStyle(assignment.event_id)}
            >
              <button
                className="store-loadout-card-header w-full text-left"
                onClick={() => {
                  setSelectedAssignmentId(assignment.id);
                  setSelectedItemId(assignment.items[0]?.id ?? null);
                }}
                type="button"
              >
                <div>
                  <p className="brand-eyebrow">{assignment.event_name}</p>
                  <h3>
                    Store {assignment.store_number}
                    {assignment.store_name ? ` · ${assignment.store_name}` : ""}
                  </h3>
                  <p>
                    Zone {assignment.loadout_zone ?? "TBD"} · departure{" "}
                    {timeLabel(assignment.recommended_departure_at)}
                  </p>
                  {assignment.team_name ||
                  assignment.team_lead_emails.length ? (
                    <p>
                      Team {assignment.team_name ?? "TBD"} · lead{" "}
                      {assignment.team_lead_emails.join(", ") || "TBD"}
                    </p>
                  ) : null}
                  {assignment.vehicle_labels.length ? (
                    <p>Vehicles: {assignment.vehicle_labels.join(", ")}</p>
                  ) : null}
                </div>
                <span
                  className={`store-loadout-status ${assignment.final_review_completed_at ? "signed_complete" : assignment.status}`}
                >
                  {statusLabel(
                    assignment.final_review_completed_at
                      ? "signed_complete"
                      : assignment.status,
                  )}
                </span>
              </button>

              <div className="store-loadout-items border-t pt-2">
                {assignment.items.map((item) => (
                  <button
                    className={`store-loadout-item w-full text-left ${selectedItemId === item.id && selectedAssignmentId === assignment.id ? "ring-2 ring-yellow-300" : ""}`}
                    key={item.id}
                    onClick={() => {
                      setSelectedAssignmentId(assignment.id);
                      setSelectedItemId(item.id);
                    }}
                    type="button"
                  >
                    <p className="brand-eyebrow">
                      {item.model_number ?? "No model"}
                    </p>
                    <h4>{item.item_name}</h4>
                    <p>
                      Qty {item.quantity_assigned} · {statusLabel(item.status)}
                    </p>
                  </button>
                ))}
              </div>
            </article>
          ))}
        </div>
        {selectedAssignment && selectedItem ? (
          <div className="store-loadout-item store-loadout-item-editor">
            <div>
              <p className="brand-eyebrow">
                Booth {selectedItem.booth_number} ·{" "}
                {selectedItem.vendor_name ?? selectedItem.vendor_code}
              </p>
              <h3>{selectedItem.item_name}</h3>
              <p>
                Model {selectedItem.model_number ?? "N/A"} · expected{" "}
                {selectedItem.quantity_assigned} · current{" "}
                {statusLabel(selectedItem.status)}
              </p>
              {selectedItem.damage_notes || selectedItem.notes ? (
                <p className="mt-2 rounded-lg border border-amber-400/40 bg-amber-400/10 p-2 text-xs text-amber-100">
                  Prior booth note:{" "}
                  {selectedItem.damage_notes || selectedItem.notes}
                </p>
              ) : null}
            </div>
            <form
              onSubmit={(event) =>
                void submitCheckin(selectedAssignment, selectedItem, event)
              }
            >
              <div className="store-loadout-item-fields">
                <label>
                  Status
                  <select
                    name="status"
                    defaultValue={
                      selectedItem.status === "assigned"
                        ? "found"
                        : selectedItem.status
                    }
                  >
                    {checkinStatuses.map((status) => (
                      <option key={status} value={status}>
                        {statusLabel(status)}
                      </option>
                    ))}
                  </select>
                </label>
                <label>
                  Qty found
                  <input
                    min="0"
                    name="quantity_found"
                    type="number"
                    defaultValue={
                      selectedItem.quantity_found ||
                      selectedItem.quantity_assigned
                    }
                  />
                </label>
              </div>
              <label>
                Damage note
                <textarea
                  name="damage_notes"
                  placeholder="Optional damage details"
                  defaultValue={selectedItem.damage_notes ?? ""}
                />
              </label>
              <label>
                Missing note
                <textarea
                  name="missing_notes"
                  placeholder="Optional missing-item details"
                  defaultValue={selectedItem.missing_notes ?? ""}
                />
              </label>
              <button
                className="brand-button"
                disabled={
                  busyKey === `${selectedAssignment.id}-${selectedItem.id}`
                }
                type="submit"
              >
                Save item
              </button>
            </form>
            <form
              className="mt-2 flex flex-wrap items-center gap-2"
              onSubmit={(event) =>
                void uploadEvidence(selectedAssignment, selectedItem, event)
              }
            >
              <input
                accept="image/jpeg,image/png,image/webp"
                name="evidence"
                required
                type="file"
              />
              <button
                className="brand-button brand-button-secondary"
                disabled={
                  busyKey ===
                  `${selectedAssignment.id}-${selectedItem.id}-evidence`
                }
                type="submit"
              >
                Upload evidence photo
              </button>
            </form>
            <button
              className="brand-button store-loadout-ready"
              disabled={
                busyKey === selectedAssignment.id ||
                Boolean(selectedAssignment.final_review_completed_at)
              }
              onClick={() => void completeStore(selectedAssignment)}
              type="button"
            >
              Complete store
            </button>
            {selectedAssignment.final_review_completed_at &&
            !selectedAssignment.signed_at ? (
              <form
                className="store-loadout-signoff"
                onSubmit={(event) =>
                  void signAssignment(selectedAssignment, event)
                }
              >
                <div>
                  <p className="brand-eyebrow">Final review</p>
                  <h4>Sign packing list</h4>
                  <p>
                    Event staff review is complete. Confirm the final packing
                    list, including any exceptions, before leaving the booth.
                  </p>
                  {selectedAssignment.final_review_notes ? (
                    <p className="store-loadout-message">
                      Review notes: {selectedAssignment.final_review_notes}
                    </p>
                  ) : null}
                </div>
                <label>
                  Signer name
                  <input
                    name="signer_name"
                    defaultValue={user?.display_name ?? ""}
                    required
                  />
                </label>
                <label>
                  Signer email
                  <input
                    name="signer_email"
                    defaultValue={user?.email ?? ""}
                    required
                    type="email"
                  />
                </label>
                <label>
                  Signature
                  <input
                    name="signature_text"
                    placeholder="Type your name to sign"
                    required
                  />
                </label>
                <label>
                  Exception summary
                  <textarea
                    name="exception_summary"
                    placeholder="Optional notes for damaged, missing, or quantity mismatch items"
                  />
                </label>
                <button
                  className="brand-button"
                  disabled={busyKey === `${selectedAssignment.id}-sign`}
                  type="submit"
                >
                  Sign final packing list
                </button>
              </form>
            ) : null}
            {selectedAssignment.signed_at ? (
              <p className="store-loadout-message">
                Signed {new Date(selectedAssignment.signed_at).toLocaleString()}{" "}
                by {selectedAssignment.signed_by ?? "store staff"}.
              </p>
            ) : null}
          </div>
        ) : (
          <p className="store-loadout-message">
            Select a store and item to begin validation.
          </p>
        )}
      </div>
      {eventId ? (
        <div className="mt-6 border-t border-yellow-300/30 pt-5">
          <div className="mb-3">
            <p className="brand-eyebrow">Loadout booth navigation</p>
            <h3 className="text-xl font-bold">Find assigned inventory</h3>
            <p>
              Use the live vendor-hall map to guide stores between booths while
              completing their packing lists.
            </p>
          </div>
          <EventVendorHallDirectory
            activeBoothId={selectedItem?.vendor_hall_booth_id ?? null}
            eventId={eventId}
            loadoutNavigation
            readOnly
          />
        </div>
      ) : null}
    </section>
  );
}
