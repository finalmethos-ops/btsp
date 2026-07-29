"use client";

import { useEffect } from "react";
import { EventLoginPage } from "@/components/EventLoginPage";
import { useAuth } from "@/lib/auth";

export default function StandaloneEventLoginPage() {
  const { user, isLoading, signOut } = useAuth();

  useEffect(() => {
    if (!user) return;
    if (user.login_context === "event") {
      window.location.assign("/events/entry");
    } else {
      signOut();
    }
  }, [signOut, user]);

  if (isLoading || user) {
    return <main className="loading-screen">Loading event access…</main>;
  }

  return <EventLoginPage />;
}
