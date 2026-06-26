'use client';

import { useEffect, useState } from 'react';
import { AvailableWorkflow, getAvailableWorkflows } from '@/lib/api';
import { useAuth } from '@/lib/auth';
import { workflowRoutes } from '@/lib/workflows';

export function DashboardShell() {
  const { user, signOut } = useAuth();
  const [workflows, setWorkflows] = useState<AvailableWorkflow[]>([]);

  useEffect(() => {
    async function loadWorkflows() {
      setWorkflows(await getAvailableWorkflows());
    }

    if (user) {
      void loadWorkflows();
    }
  }, [user]);

  if (!user) {
    return null;
  }

  const workflowLabels = new Map(workflowRoutes.map((workflow) => [workflow.code, workflow.label]));

  return (
    <main className="mx-auto max-w-5xl p-8">
      <header className="mb-8 flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">BTSP</h1>
          <p className="text-slate-600">Welcome, {user.display_name}</p>
        </div>
        <button className="rounded border border-slate-300 px-4 py-2" onClick={signOut} type="button">
          Sign out
        </button>
      </header>

      <section className="mb-8 rounded-lg bg-white p-6 shadow">
        <h2 className="text-xl font-semibold">Your Access</h2>
        <p className="mt-2 text-sm text-slate-600">Roles: {user.roles.join(', ') || 'None assigned'}</p>
        <p className="mt-1 text-sm text-slate-600">Permissions: {user.permissions.length}</p>
      </section>

      <section className="grid gap-4 md:grid-cols-2">
        {workflows.map((workflow) => (
          <a className="rounded-lg bg-white p-6 shadow transition hover:shadow-md" href={workflow.route} key={workflow.code}>
            <h3 className="text-lg font-semibold">{workflowLabels.get(workflow.code) ?? workflow.code}</h3>
            <p className="mt-2 text-sm text-slate-600">Open {workflow.code} workflow tools.</p>
          </a>
        ))}
        {workflows.length === 0 ? (
          <div className="rounded-lg bg-white p-6 shadow">
            <h3 className="text-lg font-semibold">No workflows assigned</h3>
            <p className="mt-2 text-sm text-slate-600">Contact an administrator to review your access.</p>
          </div>
        ) : null}
      </section>
    </main>
  );
}
