"use client";

import { DashboardShell } from "@/components/DashboardShell";
import { LoginForm } from "@/components/LoginForm";
import { useAuth } from "@/lib/auth";

export default function HomePage() {
  const { user, isLoading } = useAuth();

  if (isLoading) {
    return <main className="p-8">Loading BTSP...</main>;
  }

  if (!user) {
    return (
      <main className="flex min-h-screen items-center justify-center p-8">
        <LoginForm />
      </main>
    );
  }

  return <DashboardShell />;
}
