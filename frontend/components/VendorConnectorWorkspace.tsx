"use client";

import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import {
  ConnectorExecution,
  ConnectorSchedule,
  createConnectorSchedule,
  enqueueDueConnectorExecutions,
  listConnectorExecutions,
  listConnectorSchedules,
  listVendorEndpoints,
  replayConnectorExecution,
  setConnectorScheduleEnabled,
  VendorEndpoint,
} from "@/lib/vendor-integration-api";

const formatDate = (value: string | null) =>
  value ? new Date(value).toLocaleString() : "—";

export function VendorConnectorWorkspace() {
  const [endpoints, setEndpoints] = useState<VendorEndpoint[]>([]);
  const [schedules, setSchedules] = useState<ConnectorSchedule[]>([]);
  const [executions, setExecutions] = useState<ConnectorExecution[]>([]);
  const [endpointId, setEndpointId] = useState("");
  const [name, setName] = useState("Inbound polling");
  const [interval, setInterval] = useState(60);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  const load = useCallback(async () => {
    const [nextEndpoints, nextSchedules, nextExecutions] = await Promise.all([
      listVendorEndpoints(),
      listConnectorSchedules(),
      listConnectorExecutions(),
    ]);
    setEndpoints(nextEndpoints);
    setSchedules(nextSchedules);
    setExecutions(nextExecutions);
    setEndpointId((current) => current || nextEndpoints[0]?.id || "");
  }, []);

  useEffect(() => {
    void load().catch((error: unknown) =>
      setMessage(
        error instanceof Error ? error.message : "Unable to load connectors",
      ),
    );
  }, [load]);

  const counts = useMemo(
    () =>
      executions.reduce<Record<string, number>>((result, item) => {
        result[item.status] = (result[item.status] ?? 0) + 1;
        return result;
      }, {}),
    [executions],
  );

  async function run(action: () => Promise<unknown>, success: string) {
    setBusy(true);
    setMessage(null);
    try {
      await action();
      await load();
      setMessage(success);
    } catch (error) {
      setMessage(
        error instanceof Error ? error.message : "Connector operation failed",
      );
    } finally {
      setBusy(false);
    }
  }

  function submitSchedule(event: FormEvent) {
    event.preventDefault();
    void run(
      () =>
        createConnectorSchedule({
          endpoint_id: endpointId,
          name,
          interval_minutes: interval,
          max_attempts: 3,
          base_retry_seconds: 60,
        }),
      "Connector schedule created.",
    );
  }

  return (
    <main className="mx-auto max-w-7xl p-8">
      <header className="mb-8 flex items-center justify-between">
        <div>
          <Link className="text-sm text-blue-700" href="/">
            ← Dashboard
          </Link>
          <h1 className="mt-2 text-3xl font-bold">
            Vendor Connector Operations
          </h1>
          <p className="mt-1 text-slate-600">
            Schedules, worker leases, retries, and dead letters.
          </p>
        </div>
        <button
          className="rounded bg-blue-700 px-4 py-2 text-white disabled:opacity-50"
          disabled={busy}
          onClick={() =>
            void run(
              enqueueDueConnectorExecutions,
              "Due connector work was queued.",
            )
          }
          type="button"
        >
          Enqueue due work
        </button>
      </header>

      {message ? (
        <p className="mb-6 rounded bg-slate-100 p-3 text-sm">{message}</p>
      ) : null}

      <section className="mb-8 grid gap-4 sm:grid-cols-4">
        {(["queued", "running", "retry", "dead_letter"] as const).map(
          (status) => (
            <div className="rounded-lg bg-white p-5 shadow" key={status}>
              <p className="text-sm capitalize text-slate-500">
                {status.replace("_", " ")}
              </p>
              <p className="mt-1 text-3xl font-semibold">
                {counts[status] ?? 0}
              </p>
            </div>
          ),
        )}
      </section>

      <section className="mb-8 grid gap-6 lg:grid-cols-[1fr_2fr]">
        <form
          className="rounded-lg bg-white p-6 shadow"
          onSubmit={submitSchedule}
        >
          <h2 className="text-xl font-semibold">New schedule</h2>
          <label className="mt-4 block text-sm font-medium">Endpoint</label>
          <select
            className="mt-1 w-full rounded border p-2"
            onChange={(event) => setEndpointId(event.target.value)}
            required
            value={endpointId}
          >
            {endpoints.map((endpoint) => (
              <option key={endpoint.id} value={endpoint.id}>
                {endpoint.vendor_code} — {endpoint.name} ({endpoint.transport})
              </option>
            ))}
          </select>
          <label className="mt-4 block text-sm font-medium">Name</label>
          <input
            className="mt-1 w-full rounded border p-2"
            onChange={(event) => setName(event.target.value)}
            required
            value={name}
          />
          <label className="mt-4 block text-sm font-medium">
            Interval (minutes)
          </label>
          <input
            className="mt-1 w-full rounded border p-2"
            min={1}
            onChange={(event) => setInterval(Number(event.target.value))}
            type="number"
            value={interval}
          />
          <button
            className="mt-5 rounded bg-slate-900 px-4 py-2 text-white disabled:opacity-50"
            disabled={busy || !endpointId}
            type="submit"
          >
            Create schedule
          </button>
        </form>

        <div className="rounded-lg bg-white p-6 shadow">
          <h2 className="text-xl font-semibold">Schedules</h2>
          <div className="mt-4 overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b">
                  <th className="p-2">Name</th>
                  <th className="p-2">Interval</th>
                  <th className="p-2">Attempts</th>
                  <th className="p-2">Next run</th>
                  <th className="p-2"></th>
                </tr>
              </thead>
              <tbody>
                {schedules.map((schedule) => (
                  <tr className="border-b" key={schedule.id}>
                    <td className="p-2 font-medium">{schedule.name}</td>
                    <td className="p-2">{schedule.interval_minutes} min</td>
                    <td className="p-2">{schedule.max_attempts}</td>
                    <td className="p-2">{formatDate(schedule.next_run_at)}</td>
                    <td className="p-2">
                      <button
                        className="text-blue-700 disabled:opacity-50"
                        disabled={busy}
                        onClick={() =>
                          void run(
                            () =>
                              setConnectorScheduleEnabled(
                                schedule.id,
                                !schedule.is_enabled,
                              ),
                            schedule.is_enabled
                              ? "Schedule paused."
                              : "Schedule resumed.",
                          )
                        }
                        type="button"
                      >
                        {schedule.is_enabled ? "Pause" : "Resume"}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </section>

      <section className="rounded-lg bg-white p-6 shadow">
        <h2 className="text-xl font-semibold">Execution history</h2>
        <div className="mt-4 overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-b">
                <th className="p-2">Status</th>
                <th className="p-2">Attempts</th>
                <th className="p-2">Available</th>
                <th className="p-2">Worker</th>
                <th className="p-2">Last error</th>
                <th className="p-2"></th>
              </tr>
            </thead>
            <tbody>
              {executions.map((execution) => (
                <tr className="border-b align-top" key={execution.id}>
                  <td className="p-2 font-medium">
                    {execution.status.replace("_", " ")}
                  </td>
                  <td className="p-2">
                    {execution.attempt_count}/{execution.max_attempts}
                  </td>
                  <td className="p-2">{formatDate(execution.available_at)}</td>
                  <td className="p-2">{execution.worker_id ?? "—"}</td>
                  <td className="max-w-sm p-2 text-red-700">
                    {execution.error_message ?? "—"}
                  </td>
                  <td className="p-2">
                    {execution.status === "dead_letter" ? (
                      <button
                        className="text-blue-700 disabled:opacity-50"
                        disabled={busy}
                        onClick={() =>
                          void run(
                            () => replayConnectorExecution(execution.id),
                            "Dead letter queued for replay.",
                          )
                        }
                        type="button"
                      >
                        Replay
                      </button>
                    ) : null}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </main>
  );
}
