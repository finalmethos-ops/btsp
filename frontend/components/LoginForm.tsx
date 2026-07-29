"use client";

import { FormEvent, useState } from "react";
import Image from "next/image";
import Link from "next/link";
import { useAuth } from "@/lib/auth";

export function LoginForm({
  logoSrc = "/brand/purchasing-intelligence-logo.png",
  logoAlt = "Buddy's Purchasing Intelligence",
  logoHeight = 200,
  logoWidth = 200,
  title = "Welcome",
  subtitle,
  submitLabel = "Sign in",
  secondaryHref,
  secondaryLabel,
  onSignedIn,
  loginContext = "standard",
}: {
  logoSrc?: string;
  logoAlt?: string;
  logoHeight?: number;
  logoWidth?: number;
  title?: string;
  subtitle?: string;
  submitLabel?: string;
  secondaryHref?: string;
  secondaryLabel?: string;
  onSignedIn?: () => void;
  loginContext?: "standard" | "event";
}) {
  const { signIn } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setIsSubmitting(true);
    try {
      await signIn(email, password, loginContext);
      onSignedIn?.();
    } catch (caught) {
      setError(
        caught instanceof Error && caught.message
          ? caught.message
          : "Unable to sign in with those credentials.",
      );
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="login-form">
      <Image
        alt={logoAlt}
        className="login-icon"
        height={logoHeight}
        priority
        src={logoSrc}
        width={logoWidth}
      />
      {title ? <h2>{title}</h2> : null}
      {subtitle ? <p>{subtitle}</p> : null}
      <label>
        Email
        <input
          autoComplete="email"
          value={email}
          onChange={(event) => setEmail(event.target.value)}
          type="email"
          required
        />
      </label>
      <label>
        Password
        <input
          autoComplete="current-password"
          value={password}
          onChange={(event) => setPassword(event.target.value)}
          type="password"
          required
        />
      </label>
      {error ? <p className="text-sm text-red-700">{error}</p> : null}
      <button className="login-submit" disabled={isSubmitting} type="submit">
        {isSubmitting ? "Signing in..." : submitLabel}
      </button>
      <Link className="login-secondary-link" href="/password-reset">
        Forgot password?
      </Link>
      {secondaryHref && secondaryLabel ? (
        <Link className="login-secondary-link" href={secondaryHref}>
          {secondaryLabel}
        </Link>
      ) : null}
    </form>
  );
}
