"use client";

import { FormEvent, useEffect, useState } from "react";
import {
  AdminUser,
  createAdminUser,
  deleteAdminUser,
  listAdminRoles,
  listAdminUsers,
  updateAdminUser,
} from "@/lib/api";

function splitVendorCodes(value: string): string[] {
  return [
    ...new Set(
      value
        .split(",")
        .map((code) => code.trim())
        .filter(Boolean),
    ),
  ];
}

export function UserManagementPanel({
  audience = "all",
}: {
  audience?: "all" | "vendor" | "buddys";
}) {
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [roleOptions, setRoleOptions] = useState<string[]>([]);
  const [selectedEmail, setSelectedEmail] = useState<string | null>(null);
  const [email, setEmail] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [password, setPassword] = useState("");
  const [regionCode, setRegionCode] = useState("");
  const [entityCode, setEntityCode] = useState("");
  const [homeStoreNumber, setHomeStoreNumber] = useState("");
  const [vendorCodes, setVendorCodes] = useState("");
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
    setEntityCode("");
    setHomeStoreNumber("");
    setVendorCodes("");
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
    setEntityCode(user.entity_code ?? "");
    setHomeStoreNumber(user.home_store_number ?? "");
    setVendorCodes(user.vendor_codes.join(", "));
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
          password: password || undefined,
          home_store_number: homeStoreNumber || null,
          region_code: regionCode || null,
          entity_code: entityCode || null,
          vendor_codes: splitVendorCodes(vendorCodes),
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
          entity_code: entityCode || null,
          vendor_codes: splitVendorCodes(vendorCodes),
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

  async function removeSelectedUser() {
    if (
      !selectedEmail ||
      !window.confirm(`Delete ${selectedEmail}? This cannot be undone.`)
    )
      return;
    try {
      await deleteAdminUser(selectedEmail);
      await refreshUsers();
      resetForm();
    } catch {
      setError("Unable to delete this user.");
    }
  }

  const displayedUsers = users.filter((user) =>
    audience === "all"
      ? true
      : audience === "vendor"
        ? user.roles.includes("VENDOR")
        : !user.roles.includes("VENDOR"),
  );
  const heading =
    audience === "vendor"
      ? "Vendor Users"
      : audience === "buddys"
        ? "Buddy’s Users"
        : "Users";

  return (
    <div className="admin-user-directory grid gap-6 lg:grid-cols-[1fr_360px]">
      <section>
        <h2 className="text-2xl font-bold">{heading}</h2>
        <p className="mt-2 text-sm text-slate-600">
          Manage BTSP users and assigned roles.
        </p>
        <div className="event-glass-pane mt-6 overflow-x-auto rounded-xl border border-slate-200">
          <table className="w-full border-collapse text-left text-sm">
            <thead className="user-directory-table-head">
              <tr>
                <th className="p-3">Name</th>
                <th className="p-3">Email</th>
                <th className="p-3">Roles</th>
                <th className="p-3">Entity</th>
                <th className="p-3">Vendor</th>
                <th className="p-3">Status</th>
              </tr>
            </thead>
            <tbody>
              {displayedUsers.map((user) => (
                <tr
                  aria-selected={selectedEmail === user.email}
                  className={`user-directory-row border-t border-slate-200 ${
                    selectedEmail === user.email ? "selected-object" : ""
                  }`}
                  key={user.email}
                >
                  <td className="p-3">
                    <button
                      className="user-directory-selector"
                      onClick={() => selectUser(user)}
                      type="button"
                    >
                      {user.display_name}
                    </button>
                  </td>
                  <td className="p-3">{user.email}</td>
                  <td className="p-3">{user.roles.join(", ") || "None"}</td>
                  <td className="p-3">{user.entity_code ?? "—"}</td>
                  <td className="p-3">
                    {user.vendor_codes.length
                      ? user.vendor_codes.join(", ")
                      : "—"}
                  </td>
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
        className="event-glass-pane user-directory-editor rounded-xl border border-slate-200 p-4"
        onSubmit={handleSubmit}
      >
        <div className="mb-4 flex items-center justify-between">
          <h3 className="text-lg font-semibold">
            {selectedEmail ? "Edit user" : "Create user"}
          </h3>
          <button
            className="user-directory-clear text-sm"
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
        {selectedEmail ? (
          <label className="mb-3 block text-sm font-medium">
            Set new password
            <input
              className="mt-1 w-full rounded border border-slate-300 px-3 py-2"
              minLength={12}
              placeholder="Leave blank to keep current password"
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
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
          Entity code
          <input
            className="mt-1 w-full rounded border border-slate-300 px-3 py-2"
            value={entityCode}
            onChange={(event) =>
              setEntityCode(event.target.value.toUpperCase())
            }
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
        <label className="mb-3 block text-sm font-medium">
          Vendor account codes
          <input
            className="mt-1 w-full rounded border border-slate-300 px-3 py-2"
            value={vendorCodes}
            onChange={(event) =>
              setVendorCodes(event.target.value.toUpperCase())
            }
            placeholder="Comma-separated; required for Vendor role"
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
              <label
                className={`user-role-selection-pane selection-pane flex items-center gap-2 rounded-lg border p-2 text-sm ${roleCodes.includes(roleCode) ? "is-selected" : ""}`}
                key={roleCode}
              >
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
          className="user-directory-save w-full rounded-lg px-4 py-2 font-semibold"
          type="submit"
        >
          {selectedEmail ? "Update user" : "Create user"}
        </button>
        {selectedEmail ? (
          <button
            className="mt-3 w-full rounded-lg bg-red-800 px-4 py-2 font-semibold text-white"
            onClick={() => void removeSelectedUser()}
            type="button"
          >
            Delete user
          </button>
        ) : null}
      </form>
    </div>
  );
}
