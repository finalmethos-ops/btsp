"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";
import { ArchivedEventCloseoutPanel } from "@/components/ArchivedEventCloseoutPanel";
import { ProtectedRoute } from "@/components/ProtectedRoute";
import { listArchivedEvents, ManagedEvent } from "@/lib/event-admin-api";
import {
  archivedEventYears,
  ArchivedStatusFilter,
  filterArchivedEvents,
} from "@/lib/event-archive";

const dateTime = (value: string) => new Date(value).toLocaleString();

export default function ArchivedEventsPage() {
  return (
    <ProtectedRoute requiredPermission="events.manage">
      <ArchivedEventsWorkspace />
    </ProtectedRoute>
  );
}

function ArchivedEventsWorkspace() {
  const [events, setEvents] = useState<ManagedEvent[]>([]);
  const [selected, setSelected] = useState<ManagedEvent | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<ArchivedStatusFilter>("all");
  const [yearFilter, setYearFilter] = useState("all");

  const load = useCallback(async () => {
    const archived = (await listArchivedEvents()).filter((event) =>
      ["completed", "cancelled"].includes(event.status),
    );
    setEvents(archived);
    setSelected(
      (current) =>
        archived.find((event) => event.id === current?.id) ??
        archived[0] ??
        null,
    );
  }, []);

  useEffect(() => {
    void load().catch((caught: unknown) =>
      setError(
        caught instanceof Error
          ? caught.message
          : "Unable to load archived events.",
      ),
    );
  }, [load]);

  const years = useMemo(() => archivedEventYears(events), [events]);

  const filteredEvents = useMemo(
    () =>
      filterArchivedEvents(events, {
        search,
        status: statusFilter,
        year: yearFilter,
      }),
    [events, search, statusFilter, yearFilter],
  );

  useEffect(() => {
    setSelected(
      (current) =>
        filteredEvents.find((event) => event.id === current?.id) ??
        filteredEvents[0] ??
        null,
    );
  }, [filteredEvents]);

  const membershipCounts = selected?.memberships.reduce<Record<string, number>>(
    (counts, membership) => {
      counts[membership.membership_type] =
        (counts[membership.membership_type] ?? 0) + 1;
      return counts;
    },
    {},
  );

  return (
    <main className="event-ui mx-auto max-w-7xl p-4 sm:p-8">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="brand-eyebrow">Read-only reference</p>
          <h1 className="text-3xl font-bold">Archived events</h1>
          <p className="mt-2 text-slate-600">
            Completed and cancelled events are retained here without crowding
            active event workspaces.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Link className="rounded-xl border px-4 py-3 font-bold" href="/admin">
            Command Center
          </Link>
          <Link
            className="rounded-xl border px-4 py-3 font-bold"
            href="/events"
          >
            My Events
          </Link>
          <Link
            className="rounded-xl border px-4 py-3 font-bold"
            href="/admin/events"
          >
            Event Management
          </Link>
        </div>
      </div>

      {error ? (
        <p className="mt-5 rounded-xl bg-red-50 p-4 text-red-800">{error}</p>
      ) : null}

      <section className="event-glass-pane mt-6 rounded-2xl border p-4">
        <div className="grid gap-3 md:grid-cols-[minmax(0,1fr)_190px_150px]">
          <label className="grid gap-1 text-sm font-bold">
            Search archived events
            <input
              onChange={(input) => setSearch(input.target.value)}
              placeholder="Event, venue, city, or identifier"
              type="search"
              value={search}
            />
          </label>
          <label className="grid gap-1 text-sm font-bold">
            Status
            <select
              onChange={(input) =>
                setStatusFilter(input.target.value as ArchivedStatusFilter)
              }
              value={statusFilter}
            >
              <option value="all">Completed &amp; cancelled</option>
              <option value="completed">Completed only</option>
              <option value="cancelled">Cancelled only</option>
            </select>
          </label>
          <label className="grid gap-1 text-sm font-bold">
            End year
            <select
              onChange={(input) => setYearFilter(input.target.value)}
              value={yearFilter}
            >
              <option value="all">All years</option>
              {years.map((year) => (
                <option key={year} value={year}>
                  {year}
                </option>
              ))}
            </select>
          </label>
        </div>
        <p className="mt-3 text-sm text-slate-400">
          Showing {filteredEvents.length} of {events.length} archived event
          {events.length === 1 ? "" : "s"}.
        </p>
      </section>

      <div className="mt-6 grid gap-5 xl:grid-cols-[300px_1fr]">
        <aside className="space-y-2">
          {filteredEvents.map((event) => (
            <button
              className={`w-full rounded-xl border p-4 text-left ${selected?.id === event.id ? "selected-object" : "event-glass-pane"}`}
              key={event.id}
              onClick={() => setSelected(event)}
              type="button"
            >
              <strong className="block">{event.name}</strong>
              <span className="text-xs font-bold uppercase">
                {event.status}
              </span>
              <span className="mt-2 block text-xs text-slate-500">
                {new Date(event.starts_at).toLocaleDateString()}–
                {new Date(event.ends_at).toLocaleDateString()}
              </span>
            </button>
          ))}
          {!filteredEvents.length ? (
            <p className="rounded-xl border border-dashed p-4 text-sm text-slate-500">
              No archived events match these filters.
            </p>
          ) : null}
        </aside>

        {selected ? (
          <div className="space-y-5">
            <section className="rounded-2xl bg-slate-950 p-5 text-white">
              <p className="text-sm font-bold uppercase text-blue-300">
                {selected.status}
              </p>
              <h2 className="text-2xl font-bold">{selected.name}</h2>
              <p className="mt-1 text-slate-300">
                {selected.venue_name} · {selected.city}, {selected.state_code}
              </p>
              <div className="mt-4 grid gap-3 text-sm sm:grid-cols-3">
                <ReferenceMetric
                  label="Event dates"
                  value={`${dateTime(selected.starts_at)} – ${dateTime(selected.ends_at)}`}
                />
                <ReferenceMetric
                  label="Sub-events"
                  value={String(selected.sub_events.length)}
                />
                <ReferenceMetric
                  label="Attendees"
                  value={String(selected.memberships.length)}
                />
              </div>
            </section>

            {selected.status === "cancelled" ? (
              <section className="rounded-2xl border border-red-300 bg-red-50 p-5 text-red-950">
                <p className="brand-eyebrow">Cancellation record</p>
                <h3 className="text-xl font-bold">
                  {selected.cancellation_reason ?? "No reason recorded"}
                </h3>
                <p className="mt-1 text-sm">
                  Cancelled by{" "}
                  {selected.cancelled_by ?? "Unknown administrator"}
                  {selected.cancelled_at
                    ? ` on ${dateTime(selected.cancelled_at)}`
                    : ""}
                </p>
              </section>
            ) : null}

            <ArchivedEventCloseoutPanel event={selected} />

            <section className="event-glass-pane rounded-2xl border p-5">
              <p className="brand-eyebrow">Reference summary</p>
              <h3 className="text-xl font-bold">Attendance categories</h3>
              <div className="mt-3 flex flex-wrap gap-2">
                {Object.entries(membershipCounts ?? {}).map(([type, count]) => (
                  <span
                    className="rounded-full bg-blue-50 px-3 py-2 text-sm font-semibold text-blue-900"
                    key={type}
                  >
                    {type.replaceAll("_", " ")}: {count}
                  </span>
                ))}
                {!selected.memberships.length ? (
                  <span className="text-sm text-slate-500">
                    No attendees recorded.
                  </span>
                ) : null}
              </div>
            </section>

            <section className="event-glass-pane rounded-2xl border p-5">
              <p className="brand-eyebrow">Archived schedule</p>
              <h3 className="text-xl font-bold">Sub-events</h3>
              <div className="mt-4 grid gap-3 md:grid-cols-2">
                {selected.sub_events.map((subEvent) => (
                  <article
                    className="event-glass-pane rounded-xl border p-4"
                    key={subEvent.id}
                  >
                    <h4 className="font-bold">{subEvent.name}</h4>
                    <p className="text-sm text-slate-600">
                      {subEvent.location} · {dateTime(subEvent.starts_at)}
                    </p>
                    <p className="mt-2 text-xs font-bold uppercase text-slate-500">
                      {subEvent.status}
                    </p>
                    <div className="mt-3 flex flex-wrap gap-2">
                      {subEvent.module_codes.map((module) => (
                        <span
                          className="rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold"
                          key={module}
                        >
                          {module.replaceAll("-", " ")}
                        </span>
                      ))}
                    </div>
                  </article>
                ))}
                {!selected.sub_events.length ? (
                  <p className="text-sm text-slate-500">
                    No sub-events recorded.
                  </p>
                ) : null}
              </div>
            </section>
          </div>
        ) : null}
      </div>
    </main>
  );
}

function ReferenceMetric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl bg-white/10 p-3">
      <span className="block text-xs font-bold uppercase text-blue-300">
        {label}
      </span>
      <strong className="mt-1 block">{value}</strong>
    </div>
  );
}
