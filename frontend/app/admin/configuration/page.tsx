'use client';

import { FormEvent, useEffect, useState } from 'react';
import { AdminShell } from '@/components/AdminShell';
import { ProtectedRoute } from '@/components/ProtectedRoute';
import { ConfigEntry, listConfigEntries, seedConfigDefaults } from '@/lib/configuration-api';

export default function AdminConfigurationPage() {
  const [entries, setEntries] = useState<ConfigEntry[]>([]);
  const [message, setMessage] = useState<string | null>(null);
  const [scopeType, setScopeType] = useState('');
  const [scopeKey, setScopeKey] = useState('');

  async function loadEntries() {
    setEntries(await listConfigEntries(scopeType || undefined, scopeKey || undefined));
  }

  useEffect(() => {
    void loadEntries();
  }, []);

  async function handleFilter(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    await loadEntries();
  }

  async function handleSeed() {
    const result = await seedConfigDefaults();
    setMessage(`Seeded ${result.seeded_count} defaults.`);
    await loadEntries();
  }

  return (
    <ProtectedRoute requiredPermission="configuration.manage">
      <AdminShell>
        <div className="flex items-start justify-between gap-4">
          <div>
            <h2 className="text-2xl font-bold">Configuration</h2>
            <p className="mt-2 text-slate-600">Review scoped BTSP settings and seed safe defaults.</p>
          </div>
          <button className="rounded bg-slate-900 px-4 py-2 text-sm font-semibold text-white" onClick={handleSeed} type="button">
            Seed defaults
          </button>
        </div>
        <form className="mt-6 flex flex-col gap-3 md:flex-row" onSubmit={handleFilter}>
          <input className="rounded border border-slate-300 px-3 py-2" placeholder="Scope type" value={scopeType} onChange={(event) => setScopeType(event.target.value)} />
          <input className="rounded border border-slate-300 px-3 py-2" placeholder="Scope key" value={scopeKey} onChange={(event) => setScopeKey(event.target.value)} />
          <button className="rounded border border-slate-300 px-4 py-2" type="submit">Filter</button>
        </form>
        {message ? <p className="mt-4 text-sm text-green-700">{message}</p> : null}
        <div className="mt-6 space-y-3">
          {entries.map((entry) => (
            <article className="rounded border border-slate-200 p-4" key={`${entry.scope_type}:${entry.scope_key}:${entry.key}`}>
              <h3 className="font-semibold">{entry.key}</h3>
              <p className="text-sm text-slate-600">{entry.scope_type} / {entry.scope_key}</p>
              <pre className="mt-3 overflow-x-auto rounded bg-slate-100 p-3 text-xs">{JSON.stringify(entry.value, null, 2)}</pre>
            </article>
          ))}
        </div>
      </AdminShell>
    </ProtectedRoute>
  );
}
