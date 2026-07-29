"use client";

import { LoginForm } from "@/components/LoginForm";

export function EventLoginPage({
  redirectTo = "/events/entry",
}: { redirectTo?: string } = {}) {
  return (
    <main className="event-login-page">
      <section
        aria-label="Buddy's event access"
        className="event-login-brand"
      />
      <section className="event-login-panel">
        <LoginForm
          loginContext="event"
          logoAlt="Buddy's Home Furnishings"
          logoHeight={87}
          logoSrc="/brand/buddys-logo-compact.png"
          logoWidth={220}
          onSignedIn={() => window.location.assign(redirectTo)}
          secondaryHref="/"
          secondaryLabel="Use standard BTSP portal"
          submitLabel="Enter event"
          title=""
        />
      </section>
    </main>
  );
}
