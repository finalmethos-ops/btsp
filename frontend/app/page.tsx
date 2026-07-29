"use client";

import { DashboardShell } from "@/components/DashboardShell";
import { LoginForm } from "@/components/LoginForm";
import { TemporaryPasswordChange } from "@/components/TemporaryPasswordChange";
import { useAuth } from "@/lib/auth";
import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { requiresVendorSelection } from "@/lib/vendor-context";

export default function HomePage() {
  const { user, isLoading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (user?.login_context === "event") router.replace("/events/entry");
    else if (requiresVendorSelection(user)) router.replace("/vendor-select");
  }, [router, user]);

  if (isLoading) {
    return (
      <main className="loading-screen">Loading Purchasing Intelligence…</main>
    );
  }

  if (!user) {
    return (
      <main className="login-page">
        <section
          className="login-brand"
          aria-label="Buddy's Purchasing Intelligence"
        />
        <section className="login-panel">
          <LoginForm
            secondaryHref="/event-login"
            secondaryLabel="Looking for event access?"
          />
        </section>
      </main>
    );
  }

  if (user.login_context === "event") {
    return <main className="loading-screen">Returning to event access…</main>;
  }

  if (user.password_change_required) {
    return <TemporaryPasswordChange />;
  }

  if (requiresVendorSelection(user)) {
    return <main className="loading-screen">Opening vendor selection…</main>;
  }

  return <DashboardShell />;
}
