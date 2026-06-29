"use client";

import { useEffect, useState } from "react";
import { SystemDiagnostics, getSystemDiagnostics } from "@/lib/api";

function bytes(value: number | null): string {
  if (value === null) return "Unavailable";
  const gib = value / 1024 ** 3;
  return `${gib.toFixed(1)} GiB free`;
}

function duration(seconds: number): string {
  const days = Math.floor(seconds / 86400);
  const hours = Math.floor((seconds % 86400) / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  return [days ? `${days}d` : "", hours ? `${hours}h` : "", `${minutes}m`]
    .filter(Boolean)
    .join(" ");
}

function badge(status: string): string {
  if (status === "healthy") return "bg-green-100 text-green-800";
  if (status === "degraded") return "bg-amber-100 text-amber-800";
  return "bg-red-100 text-red-800";
}

export function SystemHealthPanel() {
  const [diagnostics, setDiagnostics] = useState<SystemDiagnostics | null>(
    null,
  );
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  async function refresh() {
    setLoading(true);
    setError(null);
    try {
      setDiagnostics(await getSystemDiagnostics());
    } catch (reason) {
      setError(
        reason instanceof Error
          ? reason.message
          : "Unable to load diagnostics.",
      );
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void refresh();
  }, []);

  return (
    <div>
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold">System health</h2>
          <p className="mt-2 text-sm text-slate-600">
            Dependency, storage, version, and failed-workload diagnostics.
          </p>
        </div>
        <button
          className="rounded border px-4 py-2 text-sm"
          disabled={loading}
          onClick={() => void refresh()}
          type="button"
        >
          {loading ? "Checking…" : "Refresh"}
        </button>
      </div>
      {error ? (
        <p className="mt-4 rounded bg-red-50 p-3 text-sm text-red-700">
          {error}
        </p>
      ) : null}
      {diagnostics ? (
        <div className="mt-6 space-y-6">
          <section className="rounded border p-4">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <h3 className="font-semibold">
                  {diagnostics.application} {diagnostics.version}
                </h3>
                <p className="text-sm text-slate-600">
                  {diagnostics.environment} · database{" "}
                  {diagnostics.database_revision ?? "unknown"} · uptime{" "}
                  {duration(diagnostics.uptime_seconds)}
                </p>
              </div>
              <span
                className={`rounded-full px-3 py-1 text-sm font-medium ${badge(diagnostics.status)}`}
              >
                {diagnostics.status}
              </span>
            </div>
            <p className="mt-2 text-xs text-slate-500">
              Generated {new Date(diagnostics.generated_at).toLocaleString()}
            </p>
          </section>

          <section>
            <h3 className="font-semibold">Dependencies</h3>
            <div className="mt-3 grid gap-3 md:grid-cols-2">
              {diagnostics.dependencies.map((item) => (
                <article className="rounded border p-4" key={item.name}>
                  <div className="flex justify-between gap-3">
                    <span className="font-medium capitalize">{item.name}</span>
                    <span
                      className={`rounded-full px-2 py-0.5 text-xs ${badge(item.status)}`}
                    >
                      {item.status}
                    </span>
                  </div>
                  <p className="mt-2 text-sm text-slate-600">
                    {item.latency_ms === null
                      ? (item.detail ?? "Unavailable")
                      : `${item.latency_ms.toFixed(2)} ms`}
                  </p>
                </article>
              ))}
            </div>
          </section>

          <section>
            <h3 className="font-semibold">Durable storage</h3>
            <div className="mt-3 grid gap-3 md:grid-cols-3">
              {diagnostics.storage.map((item) => (
                <article className="rounded border p-4" key={item.name}>
                  <div className="flex justify-between gap-2">
                    <span className="font-medium">
                      {item.name.replaceAll("_", " ")}
                    </span>
                    <span
                      className={`rounded-full px-2 py-0.5 text-xs ${badge(item.status)}`}
                    >
                      {item.status}
                    </span>
                  </div>
                  <p className="mt-2 text-sm text-slate-600">
                    {bytes(item.free_bytes)}
                  </p>
                  <p className="text-xs text-slate-500">
                    {item.writable ? "Writable" : "Not writable"}
                  </p>
                </article>
              ))}
            </div>
          </section>

          <section>
            <h3 className="font-semibold">Operational workloads</h3>
            <div className="mt-3 grid gap-3 md:grid-cols-3">
              {diagnostics.operational_metrics.map((item) => (
                <article
                  className={`rounded border p-4 ${item.severity === "warning" ? "border-amber-300 bg-amber-50" : ""}`}
                  key={item.name}
                >
                  <p className="text-sm text-slate-600">
                    {item.name.replaceAll("_", " ")}
                  </p>
                  <p className="mt-1 text-3xl font-bold">{item.count}</p>
                </article>
              ))}
            </div>
          </section>
        </div>
      ) : null}
    </div>
  );
}
