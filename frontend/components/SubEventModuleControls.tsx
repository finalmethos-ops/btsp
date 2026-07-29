"use client";

import { useEffect, useState } from "react";
import {
  EventModule,
  listEventModules,
  ManagedSubEvent,
  updateSubEventModules,
} from "@/lib/event-admin-api";

export function SubEventModuleControls({
  eventId,
  subEvents,
  onUpdated,
}: {
  eventId: string;
  subEvents: ManagedSubEvent[];
  onUpdated: (eventId: string) => Promise<void>;
}) {
  const [catalog, setCatalog] = useState<EventModule[]>([]);
  const [drafts, setDrafts] = useState<Record<string, string[]>>({});
  const [busyId, setBusyId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void listEventModules().then(setCatalog);
  }, []);
  useEffect(() => {
    setDrafts(
      Object.fromEntries(subEvents.map((item) => [item.id, item.module_codes])),
    );
  }, [subEvents]);

  function toggle(subEventId: string, code: string) {
    setDrafts((current) => {
      const selected = current[subEventId] ?? [];
      return {
        ...current,
        [subEventId]: selected.includes(code)
          ? selected.filter((item) => item !== code)
          : [...selected, code],
      };
    });
  }

  async function save(subEventId: string) {
    setBusyId(subEventId);
    setError(null);
    try {
      const available = new Set(catalog.map((item) => item.code));
      const selectedModules = new Set(drafts[subEventId] ?? []);
      // A product lineup is presented through the live-display controls. Keep
      // the two capabilities linked so a saved slide deck cannot disappear
      // from the presenter console.
      if (selectedModules.has("product-slides")) {
        selectedModules.add("live-display");
      }
      await updateSubEventModules(
        eventId,
        subEventId,
        [...selectedModules].filter((code) => available.has(code)),
      );
      await onUpdated(eventId);
    } catch (caught) {
      setError(
        caught instanceof Error ? caught.message : "Modules could not be saved",
      );
    } finally {
      setBusyId(null);
    }
  }

  return (
    <section className="rounded-2xl border bg-white p-5">
      <p className="brand-eyebrow">Sub-event setup</p>
      <h3 className="text-xl font-bold">Available controls</h3>
      <p className="mt-1 text-sm text-slate-600">
        Choose which BTSP tools appear inside each sub-event in My Events.
      </p>
      {error ? (
        <p className="mt-3 rounded-lg bg-red-50 p-3 text-red-800">{error}</p>
      ) : null}
      <div className="mt-4 space-y-4">
        {subEvents.map((subEvent) => (
          <article className="rounded-xl border p-4" key={subEvent.id}>
            <h4 className="font-bold">{subEvent.name}</h4>
            <p className="text-sm text-slate-500">{subEvent.location}</p>
            <div className="mt-3 grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
              {catalog.map((module) => (
                <label
                  className={`event-selectable flex cursor-pointer gap-2 rounded-lg border p-3 text-sm ${(drafts[subEvent.id] ?? []).includes(module.code) ? "is-selected" : ""}`}
                  key={module.code}
                >
                  <input
                    checked={(drafts[subEvent.id] ?? []).includes(module.code)}
                    onChange={() => toggle(subEvent.id, module.code)}
                    type="checkbox"
                  />
                  <span>
                    <strong className="block">{module.name}</strong>
                    <span className="text-xs text-slate-500">
                      {module.code}
                    </span>
                  </span>
                </label>
              ))}
            </div>
            <button
              className="mt-3 rounded-lg bg-blue-800 px-4 py-2 font-semibold text-white disabled:bg-slate-400"
              disabled={busyId === subEvent.id}
              onClick={() => void save(subEvent.id)}
              type="button"
            >
              {busyId === subEvent.id ? "Saving…" : "Save module controls"}
            </button>
          </article>
        ))}
      </div>
    </section>
  );
}
