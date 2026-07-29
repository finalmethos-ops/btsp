"use client";

import { FormEvent, useState } from "react";
import Link from "next/link";
import { confirmPasswordReset, requestPasswordReset } from "@/lib/api";

export default function PasswordResetPage() {
  const [email, setEmail] = useState("");
  const [token, setToken] = useState("");
  const [password, setPassword] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function requestReset(event: FormEvent) {
    event.preventDefault();
    setError(null);
    try {
      const result = await requestPasswordReset(email);
      setMessage(
        result.reset_token
          ? `Development reset token: ${result.reset_token}`
          : result.message,
      );
      if (result.reset_token) setToken(result.reset_token);
    } catch (caught) {
      setError(
        caught instanceof Error ? caught.message : "Unable to request reset.",
      );
    }
  }

  async function confirmReset(event: FormEvent) {
    event.preventDefault();
    setError(null);
    try {
      await confirmPasswordReset(token, password);
      setMessage("Password reset complete. Return to sign in.");
      setPassword("");
    } catch (caught) {
      setError(
        caught instanceof Error ? caught.message : "Unable to reset password.",
      );
    }
  }

  return (
    <main className="login-page">
      <section className="login-panel">
        <h1>Password reset</h1>
        <p>Request a reset link, then enter the secure token you receive.</p>
        <form className="login-form" onSubmit={requestReset}>
          <label>
            Email
            <input
              type="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              required
            />
          </label>
          <button className="login-submit" type="submit">
            Request reset
          </button>
        </form>
        <form className="login-form" onSubmit={confirmReset}>
          <label>
            Reset token
            <input
              value={token}
              onChange={(event) => setToken(event.target.value)}
              required
            />
          </label>
          <label>
            New password
            <input
              type="password"
              minLength={12}
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              required
            />
          </label>
          <button className="login-submit" type="submit">
            Set new password
          </button>
        </form>
        {message ? <p className="text-green-700">{message}</p> : null}
        {error ? <p className="text-red-700">{error}</p> : null}
        <Link className="login-secondary-link" href="/">
          Return to sign in
        </Link>
      </section>
    </main>
  );
}
