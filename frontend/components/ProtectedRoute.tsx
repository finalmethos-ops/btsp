"use client";

import Image from "next/image";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { ReactNode, useEffect } from "react";
import { EventConnectivityStatus } from "@/components/EventConnectivityStatus";
import { EventLoginPage } from "@/components/EventLoginPage";
import { EventNotificationControl } from "@/components/EventNotificationControl";
import { EventOfflineRegistration } from "@/components/EventOfflineRegistration";
import { LoginForm } from "@/components/LoginForm";
import { MessageNotificationLink } from "@/components/MessageNotificationLink";
import { TemporaryPasswordChange } from "@/components/TemporaryPasswordChange";
import { useAuth } from "@/lib/auth";
import { usesCalendarEventLanding } from "@/lib/event-landing";
import { homeDestination } from "@/lib/home-destination";
import { hasPermission } from "@/lib/permissions";
import { requiresVendorSelection } from "@/lib/vendor-context";

export function ProtectedRoute({
  children,
  loginMode = "portal",
  requiredPermission,
  loginRedirectTo,
}: {
  children: ReactNode;
  loginMode?: "portal" | "event";
  requiredPermission?: string;
  loginRedirectTo?: string;
}) {
  const { user, isLoading, signOut } = useAuth();
  const pathname = usePathname();
  const router = useRouter();
  const outsideEventScope = Boolean(
    user?.login_context === "event" && !pathname.startsWith("/events"),
  );
  const vendorSelectionRequired =
    requiresVendorSelection(user) && pathname !== "/vendor-select";

  useEffect(() => {
    if (outsideEventScope) router.replace("/events/entry");
  }, [outsideEventScope, router]);

  useEffect(() => {
    if (vendorSelectionRequired) router.replace("/vendor-select");
  }, [router, vendorSelectionRequired]);

  if (isLoading) {
    return (
      <main className="loading-screen">Loading Purchasing Intelligence…</main>
    );
  }

  if (!user) {
    if (loginMode === "event") {
      return <EventLoginPage redirectTo={loginRedirectTo} />;
    }
    return (
      <main className="login-page">
        <section
          className="login-brand"
          aria-label="Buddy's Purchasing Intelligence"
        />
        <section className="login-panel">
          <LoginForm
            loginContext="standard"
            onSignedIn={() => router.replace("/")}
          />
        </section>
      </main>
    );
  }

  if (outsideEventScope) {
    return <main className="loading-screen">Returning to event access…</main>;
  }

  if (vendorSelectionRequired) {
    return <main className="loading-screen">Opening vendor selection…</main>;
  }

  if (user.password_change_required) {
    return <TemporaryPasswordChange />;
  }

  const eventAttendee = usesCalendarEventLanding(user);
  const eventSession = user.login_context === "event";
  const home = homeDestination(user);
  const accessDenied = Boolean(
    requiredPermission && !hasPermission(user, requiredPermission),
  );

  return (
    <div className="module-page-shell">
      {eventAttendee ? <EventOfflineRegistration /> : null}
      <header
        className={`module-brand-bar ${eventAttendee ? "event-attendee-brand-bar" : ""}`}
      >
        <Link aria-label={home.ariaLabel} href={home.href}>
          <Image
            alt="Buddy's Home Furnishings"
            height={54}
            priority
            src="/brand/buddys-logo-compact.png"
            width={135}
          />
        </Link>
        <div className="flex items-center gap-3">
          {eventAttendee ? (
            <span className="event-attendee-header-name">
              {user.display_name}
            </span>
          ) : null}
          {eventAttendee ? <EventNotificationControl /> : null}
          {!eventSession ? <MessageNotificationLink /> : null}
          <Link
            aria-label={home.ariaLabel}
            className="module-home-link"
            href={home.href}
            title={home.ariaLabel}
          >
            <svg
              aria-hidden="true"
              className="nav-action-icon"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d="m3 10 9-7 9 7" />
              <path d="M5 9.5V21h14V9.5" />
              <path d="M9 21v-7h6v7" />
            </svg>
            <span className="nav-action-label">{home.label}</span>
          </Link>
          <button
            aria-label="Sign out"
            className="module-home-link nav-signout-action"
            onClick={() => {
              const destination =
                user.login_context === "event" ? "/event-login" : "/";
              signOut();
              router.replace(destination);
            }}
            title="Sign out"
            type="button"
          >
            <svg
              aria-hidden="true"
              className="nav-action-icon"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d="M10 17l5-5-5-5" />
              <path d="M15 12H3" />
              <path d="M21 3v18" />
            </svg>
            <span className="nav-action-label">Sign out</span>
          </button>
        </div>
      </header>
      {eventAttendee ? <EventConnectivityStatus /> : null}
      {accessDenied ? (
        <main className="access-denied">
          <span className="brand-badge">Protected workspace</span>
          <h1 className="text-3xl font-bold">Access denied</h1>
          <p className="mt-4 text-slate-600">
            You do not have permission to view this page. Use Home to return to
            your main workspace.
          </p>
        </main>
      ) : (
        children
      )}
    </div>
  );
}
