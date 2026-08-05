"use client";

import { FormEvent, useEffect, useState } from "react";
import { VendorHallLiveMap } from "@/components/VendorHallLiveMap";
import { useEventScope } from "@/components/EventScopeProvider";
import { listMyEventCalendar } from "@/lib/event-calendar-api";
import {
  getVendorHallDirectory,
  getVendorHallDirectoryContent,
  listMyVendorHallBooths,
  messageVendorHallDirectoryBooth,
  removeVendorHallDirectoryBooth,
  saveVendorHallDirectoryBooth,
  setVendorHallDirectoryBoothVisited,
  VendorHallDirectory,
} from "@/lib/vendor-hall-api";
import { listMyStoreLoadoutAssignments } from "@/lib/store-loadout-api";
import { cacheEventData, readCachedEventData } from "@/lib/event-offline-cache";
import { useOnlineStatus } from "@/lib/use-online-status";
import { useAuth } from "@/lib/auth";

type DirectoryView = {
  directory: VendorHallDirectory;
  sourceUrl: string | null;
};

export function EventVendorHallDirectory({
  eventId: requestedEventId,
  readOnly = false,
  loadoutNavigation = false,
  activeBoothId = null,
}: {
  eventId?: string;
  readOnly?: boolean;
  loadoutNavigation?: boolean;
  activeBoothId?: string | null;
} = {}) {
  const { user } = useAuth();
  const eventId = useEventScope();
  const [views, setViews] = useState<DirectoryView[]>([]);
  const [boothActions, setBoothActions] = useState<
    Record<string, { inventory: boolean; loadout: boolean }>
  >({});
  const [contact, setContact] = useState<{
    eventId: string;
    boothIds: string[];
    label: string;
  } | null>(null);
  const [contactBusy, setContactBusy] = useState(false);
  const [contactMessage, setContactMessage] = useState<string | null>(null);
  const [offlineSnapshot, setOfflineSnapshot] = useState(false);
  const online = useOnlineStatus();
  const allowContactRepresentatives =
    !readOnly && !user?.roles.includes("VENDOR");
  const vendorReadOnly = Boolean(user?.roles.includes("VENDOR"));

  useEffect(() => {
    let active = true;
    const urls: string[] = [];
    let cacheExpiresAt: string | null = null;
    void Promise.all([
      listMyEventCalendar(),
      listMyVendorHallBooths().catch(() => []),
      listMyStoreLoadoutAssignments().catch(() => []),
    ])
      .then(([entries, assignedBooths, loadoutAssignments]) => {
        cacheExpiresAt =
          entries
            .map((entry) => entry.ends_at)
            .sort(
              (left, right) =>
                new Date(right).getTime() - new Date(left).getTime(),
            )[0] ?? null;
        const scopedEntries = eventId
          ? entries.filter((entry) => entry.event_id === eventId)
          : entries;
        const scopedBooths = eventId
          ? assignedBooths.filter((booth) => booth.event_id === eventId)
          : assignedBooths;
        const scopedAssignments = eventId
          ? loadoutAssignments.filter(
              (assignment) => assignment.event_id === eventId,
            )
          : loadoutAssignments;
        const actions: Record<
          string,
          { inventory: boolean; loadout: boolean }
        > = {};
        scopedBooths.forEach((booth) => {
          actions[booth.id] = { inventory: true, loadout: false };
        });
        scopedAssignments
          .flatMap((assignment) => assignment.items)
          .forEach((item) => {
            actions[item.vendor_hall_booth_id] = {
              inventory: actions[item.vendor_hall_booth_id]?.inventory ?? false,
              loadout: true,
            };
          });
        if (active) setBoothActions(actions);
        return requestedEventId
          ? [requestedEventId]
          : [
              ...new Set(
                scopedEntries
                  .filter((entry) =>
                    entry.module_codes.includes("vendor-hall-setup"),
                  )
                  .map((entry) => entry.event_id),
              ),
            ];
      })
      .then((eventIds) =>
        Promise.all(
          eventIds.map(async (eventId) => {
            const directory = await getVendorHallDirectory(eventId);
            let sourceUrl: string | null = null;
            try {
              const content = await getVendorHallDirectoryContent(eventId);
              sourceUrl = URL.createObjectURL(content);
              urls.push(sourceUrl);
            } catch {
              // A digitized map can still render when no source image exists.
            }
            return { directory, sourceUrl };
          }),
        ),
      )
      .then((items) => {
        if (cacheExpiresAt) {
          cacheEventData(
            "vendor-hall-directory",
            items.map((item) => ({ ...item, sourceUrl: null })),
            cacheExpiresAt,
          );
        }
        if (active) {
          setViews(items);
          setOfflineSnapshot(false);
        }
      })
      .catch(() => {
        const cached = readCachedEventData<DirectoryView[]>(
          "vendor-hall-directory",
        );
        if (active && cached?.length) {
          setViews(
            eventId
              ? cached.filter((item) => item.directory.event_id === eventId)
              : cached,
          );
          setOfflineSnapshot(true);
        }
      });
    return () => {
      active = false;
      urls.forEach((url) => URL.revokeObjectURL(url));
    };
  }, [eventId, requestedEventId, user]);

  if (!views.length) return null;

  async function toggleSaved(
    eventId: string,
    boothIds: string[],
    shouldSave: boolean,
  ) {
    await Promise.all(
      boothIds.map((boothId) =>
        shouldSave
          ? saveVendorHallDirectoryBooth(eventId, boothId)
          : removeVendorHallDirectoryBooth(eventId, boothId),
      ),
    );
    setViews((current) =>
      current.map((view) =>
        view.directory.event_id === eventId
          ? {
              ...view,
              directory: {
                ...view.directory,
                booths: view.directory.booths.map((booth) =>
                  boothIds.includes(booth.id)
                    ? { ...booth, is_saved: shouldSave, is_visited: false }
                    : booth,
                ),
              },
            }
          : view,
      ),
    );
  }

  async function toggleVisited(
    eventId: string,
    boothIds: string[],
    visited: boolean,
  ) {
    await Promise.all(
      boothIds.map((boothId) =>
        setVendorHallDirectoryBoothVisited(eventId, boothId, visited),
      ),
    );
    setViews((current) =>
      current.map((view) =>
        view.directory.event_id === eventId
          ? {
              ...view,
              directory: {
                ...view.directory,
                booths: view.directory.booths.map((booth) =>
                  boothIds.includes(booth.id)
                    ? { ...booth, is_visited: visited }
                    : booth,
                ),
              },
            }
          : view,
      ),
    );
  }

  async function sendInquiry(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!contact) return;
    const data = new FormData(event.currentTarget);
    setContactBusy(true);
    setContactMessage(null);
    try {
      const results = await Promise.all(
        contact.boothIds.map((boothId) =>
          messageVendorHallDirectoryBooth(contact.eventId, boothId, {
            subject: String(data.get("subject")),
            body: String(data.get("body")),
          }),
        ),
      );
      const count = results.reduce((total, item) => total + item.sent_count, 0);
      setContactMessage(
        `Inquiry sent to ${count} vendor representative${count === 1 ? "" : "s"}.`,
      );
      event.currentTarget.reset();
      setContact(null);
    } catch (caught) {
      setContactMessage(
        caught instanceof Error
          ? caught.message
          : "Unable to send the inquiry.",
      );
    } finally {
      setContactBusy(false);
    }
  }

  return (
    <section className="event-ui mb-6 rounded-2xl border bg-white p-4 sm:p-5">
      <p className="brand-eyebrow">Show directory</p>
      <h2 className="text-2xl font-bold">Vendor hall map</h2>
      <p className="mb-4 text-sm text-slate-600">
        Tap a booth to view its vendor and location. Operational inventory and
        exception details remain private.
      </p>
      {offlineSnapshot ? (
        <p className="event-offline-badge mb-4">Offline map snapshot</p>
      ) : null}
      <div className="space-y-5">
        {views.map(({ directory, sourceUrl }) => (
          <VendorHallLiveMap
            activeBoothId={loadoutNavigation ? activeBoothId : null}
            directoryMode
            offlineReadOnly={offlineSnapshot || !online}
            boothActions={boothActions}
            key={directory.event_id}
            mapStatus={directory}
            onToggleSaved={(boothIds, shouldSave) =>
              toggleSaved(directory.event_id, boothIds, shouldSave)
            }
            onToggleVisited={(boothIds, visited) =>
              toggleVisited(directory.event_id, boothIds, visited)
            }
            onContactRepresentatives={(boothIds, label) => {
              setContact({ eventId: directory.event_id, boothIds, label });
              setContactMessage(null);
            }}
            allowContactRepresentatives={allowContactRepresentatives}
            hideDirectoryTools={vendorReadOnly || readOnly}
            highlightedBoothIds={
              loadoutNavigation
                ? Object.entries(boothActions)
                    .filter(([, actions]) => actions.loadout)
                    .map(([boothId]) => boothId)
                : []
            }
            sourceUrl={sourceUrl}
          />
        ))}
      </div>
      {contact ? (
        <form className="vendor-hall-contact-form" onSubmit={sendInquiry}>
          <div>
            <p className="brand-eyebrow">Private event meeting request</p>
            <h3>Request a meeting with {contact.label}</h3>
            <p>
              Your request is delivered through BTSP. Representative email
              addresses remain private; include your preferred meeting time in
              the message.
            </p>
          </div>
          <label>
            Subject
            <input
              defaultValue={`Meeting request for ${contact.label}`}
              maxLength={255}
              name="subject"
              required
            />
          </label>
          <label>
            Message
            <textarea maxLength={5000} name="body" required />
          </label>
          <div className="flex flex-wrap gap-2">
            <button className="brand-button" disabled={contactBusy}>
              {contactBusy ? "Sending…" : "Send inquiry"}
            </button>
            <button
              className="rounded-lg border px-4 py-2 font-bold"
              onClick={() => setContact(null)}
              type="button"
            >
              Cancel
            </button>
          </div>
        </form>
      ) : null}
      {contactMessage ? (
        <p className="mt-3 rounded-xl border bg-white p-3 text-sm font-semibold text-slate-800">
          {contactMessage}
        </p>
      ) : null}
    </section>
  );
}
