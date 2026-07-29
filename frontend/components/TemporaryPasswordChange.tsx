"use client";

import { FormEvent, useState } from "react";
import { useAuth } from "@/lib/auth";

export function TemporaryPasswordChange() {
  const { updatePassword } = useAuth();
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    if (newPassword !== confirmPassword) {
      setError("The new password and confirmation do not match.");
      return;
    }
    setSaving(true);
    try {
      await updatePassword(currentPassword, newPassword);
    } catch (changeError) {
      setError(
        changeError instanceof Error
          ? changeError.message
          : "Unable to update your password.",
      );
    } finally {
      setSaving(false);
    }
  }

  return (
    <main className="temporary-password-page">
      <form className="temporary-password-panel" onSubmit={submit}>
        <span className="brand-badge">Account security</span>
        <h1>Create your password</h1>
        <p>Your temporary password must be replaced before you can continue.</p>
        <label>
          Temporary password
          <input
            autoComplete="current-password"
            onChange={(event) => setCurrentPassword(event.target.value)}
            required
            type="password"
            value={currentPassword}
          />
        </label>
        <label>
          New password
          <input
            autoComplete="new-password"
            minLength={12}
            onChange={(event) => setNewPassword(event.target.value)}
            required
            type="password"
            value={newPassword}
          />
        </label>
        <label>
          Confirm new password
          <input
            autoComplete="new-password"
            minLength={12}
            onChange={(event) => setConfirmPassword(event.target.value)}
            required
            type="password"
            value={confirmPassword}
          />
        </label>
        {error ? <p className="form-error">{error}</p> : null}
        <button className="user-directory-save" disabled={saving} type="submit">
          {saving ? "Saving…" : "Save new password"}
        </button>
      </form>
    </main>
  );
}
