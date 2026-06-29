"use client";

import { useEffect, useState } from "react";
import {
  WorkflowDefinitionAdmin,
  listWorkflowDefinitionsAdmin,
  setWorkflowDefinitionActivation,
} from "@/lib/api";

export function WorkflowAdministrationPanel() {
  const [definitions, setDefinitions] = useState<WorkflowDefinitionAdmin[]>([]);
  const [busyId, setBusyId] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function refresh() {
    setDefinitions(await listWorkflowDefinitionsAdmin());
  }

  useEffect(() => {
    void refresh().catch(() =>
      setError("Unable to load workflow definitions."),
    );
  }, []);

  async function toggle(definition: WorkflowDefinitionAdmin) {
    setBusyId(definition.id);
    setError(null);
    try {
      await setWorkflowDefinitionActivation(
        definition.code,
        definition.version,
        !definition.is_active,
      );
      await refresh();
    } catch (reason) {
      setError(
        reason instanceof Error ? reason.message : "Unable to update workflow.",
      );
    } finally {
      setBusyId(null);
    }
  }

  const groups = definitions.reduce<Record<string, WorkflowDefinitionAdmin[]>>(
    (result, item) => {
      (result[item.code] ??= []).push(item);
      return result;
    },
    {},
  );

  return (
    <div>
      <h2 className="text-2xl font-bold">Workflow administration</h2>
      <p className="mt-2 text-sm text-slate-600">
        Inspect versioned definitions and control which version accepts new
        work. Running instances remain pinned to the version on which they
        started.
      </p>
      {error ? (
        <p className="mt-4 rounded bg-red-50 p-3 text-sm text-red-700">
          {error}
        </p>
      ) : null}
      <div className="mt-6 space-y-6">
        {Object.entries(groups).map(([code, versions]) => (
          <section className="rounded border border-slate-200" key={code}>
            <header className="flex items-center justify-between bg-slate-50 p-4">
              <div>
                <h3 className="font-semibold">{versions[0]?.name ?? code}</h3>
                <p className="text-xs text-slate-500">{code}</p>
              </div>
              <span className="text-sm text-slate-600">
                {versions.length} version{versions.length === 1 ? "" : "s"}
              </span>
            </header>
            <div className="divide-y divide-slate-200">
              {versions.map((definition) => (
                <article className="p-4" key={definition.id}>
                  <div className="flex flex-wrap items-start justify-between gap-4">
                    <div>
                      <div className="flex items-center gap-2">
                        <h4 className="font-medium">
                          Version {definition.version}
                        </h4>
                        <span
                          className={`rounded-full px-2 py-0.5 text-xs ${
                            definition.is_active
                              ? "bg-green-100 text-green-800"
                              : "bg-slate-200 text-slate-700"
                          }`}
                        >
                          {definition.is_active ? "Active" : "Inactive"}
                        </span>
                      </div>
                      <p className="mt-1 text-sm text-slate-600">
                        Initial: {definition.initial_state} · Terminal:{" "}
                        {definition.terminal_states.join(", ") || "None"}
                      </p>
                      <p className="mt-1 text-xs text-slate-500">
                        {definition.states.length} states ·{" "}
                        {definition.transitions.length} transitions ·{" "}
                        {definition.active_instance_count} active /{" "}
                        {definition.total_instance_count} total instances
                      </p>
                    </div>
                    <button
                      className={`rounded px-4 py-2 text-sm font-medium ${
                        definition.is_active
                          ? "border border-amber-300 text-amber-800"
                          : "bg-slate-900 text-white"
                      }`}
                      disabled={busyId !== null}
                      onClick={() => void toggle(definition)}
                      type="button"
                    >
                      {busyId === definition.id
                        ? "Updating…"
                        : definition.is_active
                          ? "Pause new instances"
                          : "Activate version"}
                    </button>
                  </div>
                  <details className="mt-3 text-sm">
                    <summary className="cursor-pointer text-slate-700">
                      Definition details
                    </summary>
                    <div className="mt-2 grid gap-3 rounded bg-slate-50 p-3 md:grid-cols-2">
                      <div>
                        <span className="font-medium">States</span>
                        <p className="text-slate-600">
                          {definition.states.join(" → ")}
                        </p>
                      </div>
                      <div>
                        <span className="font-medium">
                          Configuration namespace
                        </span>
                        <p className="text-slate-600">
                          {definition.configuration_namespace ?? "None"}
                        </p>
                      </div>
                    </div>
                  </details>
                </article>
              ))}
            </div>
          </section>
        ))}
        {!definitions.length && !error ? (
          <p className="text-sm text-slate-500">
            No workflow definitions are installed.
          </p>
        ) : null}
      </div>
    </div>
  );
}
