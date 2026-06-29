"use client";

import { ReactNode } from "react";
import { LoginForm } from "@/components/LoginForm";
import { useAuth } from "@/lib/auth";
import { hasPermission } from "@/lib/permissions";

export function ProtectedRoute({
  children,
  requiredPermission,
}: {
  children: ReactNode;
  requiredPermission?: string;
}) {
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

  if (requiredPermission && !hasPermission(user, requiredPermission)) {
    return (
      <main className="mx-auto max-w-3xl p-8">
        <h1 className="text-3xl font-bold">Access denied</h1>
        <p className="mt-4 text-slate-600">
          You do not have permission to view this page.
        </p>
      </main>
    );
  }

  return <>{children}</>;
}
