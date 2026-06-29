"use client";

import { FormEvent, useEffect, useState } from "react";
import {
  AdminPermission,
  AdminRole,
  createAdminRole,
  deleteAdminRole,
  listAdminPermissions,
  listAdminRoles,
  updateAdminRole,
} from "@/lib/api";

export function RoleManagementPanel() {
  const [roles, setRoles] = useState<AdminRole[]>([]);
  const [permissions, setPermissions] = useState<AdminPermission[]>([]);
  const [selected, setSelected] = useState<AdminRole | null>(null);
  const [code, setCode] = useState("");
  const [name, setName] = useState("");
  const [workflowCode, setWorkflowCode] = useState("");
  const [permissionCodes, setPermissionCodes] = useState<string[]>([]);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function refresh() {
    const [nextRoles, nextPermissions] = await Promise.all([
      listAdminRoles(),
      listAdminPermissions(),
    ]);
    setRoles(nextRoles);
    setPermissions(nextPermissions);
  }

  useEffect(() => {
    void refresh().catch(() => setError("Unable to load roles."));
  }, []);

  function clear() {
    setSelected(null);
    setCode("");
    setName("");
    setWorkflowCode("");
    setPermissionCodes([]);
    setMessage(null);
    setError(null);
  }

  function selectRole(role: AdminRole) {
    setSelected(role);
    setCode(role.code);
    setName(role.name);
    setWorkflowCode(role.workflow_code ?? "");
    setPermissionCodes(role.permission_codes);
    setMessage(null);
    setError(null);
  }

  function togglePermission(permissionCode: string) {
    setPermissionCodes((current) =>
      current.includes(permissionCode)
        ? current.filter((item) => item !== permissionCode)
        : [...current, permissionCode],
    );
  }

  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setMessage(null);
    setError(null);
    try {
      if (selected) {
        await updateAdminRole(selected.code, {
          name,
          workflow_code: workflowCode || null,
          permission_codes: permissionCodes,
        });
        setMessage("Role updated.");
      } else {
        await createAdminRole({
          code,
          name,
          workflow_code: workflowCode || null,
          permission_codes: permissionCodes,
        });
        setMessage("Role created.");
      }
      await refresh();
      clear();
    } catch (reason) {
      setError(
        reason instanceof Error ? reason.message : "Unable to save role.",
      );
    }
  }

  async function remove() {
    if (!selected || selected.is_system_role) return;
    setError(null);
    try {
      await deleteAdminRole(selected.code);
      await refresh();
      clear();
    } catch (reason) {
      setError(
        reason instanceof Error ? reason.message : "Unable to delete role.",
      );
    }
  }

  const locked = selected?.is_system_role ?? false;

  return (
    <div className="grid gap-6 lg:grid-cols-[1fr_420px]">
      <section>
        <h2 className="text-2xl font-bold">Roles</h2>
        <p className="mt-2 text-sm text-slate-600">
          Build custom permission sets. Platform roles are visible but
          protected.
        </p>
        <div className="mt-6 overflow-x-auto rounded border border-slate-200">
          <table className="w-full text-left text-sm">
            <thead className="bg-slate-100">
              <tr>
                <th className="p-3">Role</th>
                <th className="p-3">Permissions</th>
                <th className="p-3">Users</th>
                <th className="p-3">Type</th>
              </tr>
            </thead>
            <tbody>
              {roles.map((role) => (
                <tr className="border-t border-slate-200" key={role.code}>
                  <td className="p-3">
                    <button
                      className="font-medium underline"
                      onClick={() => selectRole(role)}
                      type="button"
                    >
                      {role.name}
                    </button>
                    <div className="text-xs text-slate-500">{role.code}</div>
                  </td>
                  <td className="p-3">{role.permission_codes.length}</td>
                  <td className="p-3">{role.user_count}</td>
                  <td className="p-3">
                    {role.is_system_role ? "System" : "Custom"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <form className="rounded border border-slate-200 p-4" onSubmit={save}>
        <div className="mb-4 flex items-center justify-between">
          <h3 className="text-lg font-semibold">
            {selected ? "Role details" : "Create role"}
          </h3>
          <button className="text-sm underline" onClick={clear} type="button">
            Clear
          </button>
        </div>
        {locked ? (
          <p className="mb-4 rounded bg-amber-50 p-3 text-sm text-amber-900">
            System roles are maintained by BTSP releases and cannot be edited.
          </p>
        ) : null}
        <label className="mb-3 block text-sm font-medium">
          Code
          <input
            className="mt-1 w-full rounded border px-3 py-2 uppercase"
            disabled={Boolean(selected)}
            onChange={(event) => setCode(event.target.value.toUpperCase())}
            pattern="[A-Z][A-Z0-9_]*"
            required
            value={code}
          />
        </label>
        <label className="mb-3 block text-sm font-medium">
          Name
          <input
            className="mt-1 w-full rounded border px-3 py-2"
            disabled={locked}
            onChange={(event) => setName(event.target.value)}
            required
            value={name}
          />
        </label>
        <label className="mb-4 block text-sm font-medium">
          Workflow code (optional)
          <input
            className="mt-1 w-full rounded border px-3 py-2"
            disabled={locked}
            onChange={(event) => setWorkflowCode(event.target.value)}
            value={workflowCode}
          />
        </label>
        <fieldset
          className="max-h-80 overflow-y-auto rounded border p-3"
          disabled={locked}
        >
          <legend className="px-1 text-sm font-medium">Permissions</legend>
          <div className="space-y-2">
            {permissions.map((permission) => (
              <label className="flex gap-2 text-sm" key={permission.code}>
                <input
                  checked={permissionCodes.includes(permission.code)}
                  onChange={() => togglePermission(permission.code)}
                  type="checkbox"
                />
                <span>
                  <span className="font-medium">{permission.code}</span>
                  <span className="block text-xs text-slate-500">
                    {permission.description}
                  </span>
                </span>
              </label>
            ))}
          </div>
        </fieldset>
        {message ? (
          <p className="mt-3 text-sm text-green-700">{message}</p>
        ) : null}
        {error ? <p className="mt-3 text-sm text-red-700">{error}</p> : null}
        {!locked ? (
          <div className="mt-4 flex gap-2">
            <button
              className="flex-1 rounded bg-slate-900 px-4 py-2 text-white"
              type="submit"
            >
              {selected ? "Update role" : "Create role"}
            </button>
            {selected ? (
              <button
                className="rounded border border-red-300 px-4 py-2 text-red-700"
                onClick={() => void remove()}
                type="button"
              >
                Delete
              </button>
            ) : null}
          </div>
        ) : null}
      </form>
    </div>
  );
}
