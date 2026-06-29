"use client";

import { FormEvent, useEffect, useState } from "react";
import {
  AdminUser,
  createAdminUser,
  listAdminRoles,
  listAdminUsers,
  updateAdminUser,
} from "@/lib/api";

export function UserManagementPanel() {
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [roleOptions, setRoleOptions] = useState<string[]>([]);
  const [selectedEmail, setSelectedEmail] = useState<string | null>(null);
  const [email, setEmail] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [password, setPassword] = useState("");
  const [regionCode, setRegionCode] = useState("");
  const [homeStoreNumber, setHomeStoreNumber] = useState("");
  const [isActive, setIsActive] = useState(true);
  const [roleCodes, setRoleCodes] = useState<string[]>([]);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function refreshUsers() {
    setUsers(await listAdminUsers());
  }

  useEffect(() => {
    void refreshUsers();
    void listAdminRoles().then((roles) =>
      setRoleOptions(roles.map((role) => role.code)),
    );
  }, []);

  function resetForm() {
    setSelectedEmail(null);
    setEmail("");
    setDisplayName("");
    setPassword("");
    setRegionCode("");
    setHomeStoreNumber("");
    setIsActive(true);
    setRoleCodes([]);
    setMessage(null);
    setError(null);
  }

  function selectUser(user: AdminUser) {
    setSelectedEmail(user.email);
    setEmail(user.email);
    setDisplayName(user.display_name);
    setPassword("");
    setRegionCode(user.region_code ?? "");
    setHomeStoreNumber(user.home_store_number ?? "");
    setIsActive(user.is_active);
    setRoleCodes(user.roles);
    setMessage(null);
    setError(null);
  }

  function toggleRole(roleCode: string) {
    setRoleCodes((current) =>
      current.includes(roleCode)
        ? current.filter((code) => code !== roleCode)
        : [...current, roleCode],
    );
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setMessage(null);
    setError(null);

    try {
      if (selectedEmail) {
        await updateAdminUser(selectedEmail, {
          display_name: displayName,
          home_store_number: homeStoreNumber || null,
          region_code: regionCode || null,
          is_active: isActive,
          role_codes: roleCodes,
        });
        setMessage("User updated.");
      } else {
        await createAdminUser({
          email,
          display_name: displayName,
          password,
          home_store_number: homeStoreNumber || null,
          region_code: regionCode || null,
          is_active: isActive,
          role_codes: roleCodes,
        });
        setMessage("User created.");
      }
      await refreshUsers();
      resetForm();
    } catch {
      setError("Unable to save user. Review the fields and try again.");
    }
  }

  return (
    <div className="grid gap-6 lg:grid-cols-[1fr_360px]">
      <section>
        <h2 className="text-2xl font-bold">Users</h2>
        <p className="mt-2 text-sm text-slate-600">
          Manage BTSP users and assigned roles.
        </p>
        <div className="mt-6 overflow-x-auto rounded border border-slate-200">
          <table className="w-full border-collapse text-left text-sm">
            <thead className="bg-slate-100 text-slate-700">
              <tr>
                <th className="p-3">Name</th>
                <th className="p-3">Email</th>
                <th className="p-3">Roles</th>
                <th className="p-3">Status</th>
              </tr>
            </thead>
            <tbody>
              {users.map((user) => (
                <tr
                  className="border-t border-slate-200 hover:bg-slate-50"
                  key={user.email}
                >
                  <td className="p-3">
                    <button
                      className="font-medium text-slate-900 underline"
                      onClick={() => selectUser(user)}
                      type="button"
                    >
                      {user.display_name}
                    </button>
                  </td>
                  <td className="p-3">{user.email}</td>
                  <td className="p-3">{user.roles.join(", ") || "None"}</td>
                  <td className="p-3">
                    {user.is_active ? "Active" : "Inactive"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <form
        className="rounded border border-slate-200 p-4"
        onSubmit={handleSubmit}
      >
        <div className="mb-4 flex items-center justify-between">
          <h3 className="text-lg font-semibold">
            {selectedEmail ? "Edit user" : "Create user"}
          </h3>
          <button
            className="text-sm text-slate-600 underline"
            onClick={resetForm}
            type="button"
          >
            Clear
          </button>
        </div>
        <label className="mb-3 block text-sm font-medium">
          Email
          <input
            className="mt-1 w-full rounded border border-slate-300 px-3 py-2"
            disabled={Boolean(selectedEmail)}
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            required
          />
        </label>
        <label className="mb-3 block text-sm font-medium">
          Display name
          <input
            className="mt-1 w-full rounded border border-slate-300 px-3 py-2"
            value={displayName}
            onChange={(event) => setDisplayName(event.target.value)}
            required
          />
        </label>
        {!selectedEmail ? (
          <label className="mb-3 block text-sm font-medium">
            Password
            <input
              className="mt-1 w-full rounded border border-slate-300 px-3 py-2"
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              required
            />
          </label>
        ) : null}
        <label className="mb-3 block text-sm font-medium">
          Region code
          <input
            className="mt-1 w-full rounded border border-slate-300 px-3 py-2"
            value={regionCode}
            onChange={(event) => setRegionCode(event.target.value)}
          />
        </label>
        <label className="mb-3 block text-sm font-medium">
          Home store number
          <input
            className="mt-1 w-full rounded border border-slate-300 px-3 py-2"
            value={homeStoreNumber}
            onChange={(event) => setHomeStoreNumber(event.target.value)}
          />
        </label>
        <label className="mb-4 flex items-center gap-2 text-sm font-medium">
          <input
            checked={isActive}
            onChange={(event) => setIsActive(event.target.checked)}
            type="checkbox"
          />
          Active
        </label>
        <fieldset className="mb-4">
          <legend className="mb-2 text-sm font-medium">Roles</legend>
          <div className="flex flex-col gap-2">
            {roleOptions.map((roleCode) => (
              <label className="flex items-center gap-2 text-sm" key={roleCode}>
                <input
                  checked={roleCodes.includes(roleCode)}
                  onChange={() => toggleRole(roleCode)}
                  type="checkbox"
                />
                {roleCode}
              </label>
            ))}
          </div>
        </fieldset>
        {message ? (
          <p className="mb-3 text-sm text-green-700">{message}</p>
        ) : null}
        {error ? <p className="mb-3 text-sm text-red-700">{error}</p> : null}
        <button
          className="w-full rounded bg-slate-900 px-4 py-2 font-semibold text-white"
          type="submit"
        >
          {selectedEmail ? "Update user" : "Create user"}
        </button>
      </form>
    </div>
  );
}
