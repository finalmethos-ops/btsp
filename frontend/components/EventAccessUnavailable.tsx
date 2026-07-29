"use client";

import Link from "next/link";

export function EventAccessUnavailable({
  message,
  title = "Event access unavailable",
}: {
  message?: string | null;
  title?: string;
}) {
  return (
    <main className="event-ui flex min-h-screen items-center justify-center bg-slate-950 p-4 text-white">
      <section className="w-full max-w-lg rounded-3xl border border-blue-400/30 bg-slate-900/90 p-6 text-center shadow-2xl shadow-blue-950/40">
        <p className="brand-eyebrow">Event workspace</p>
        <h1 className="mt-2 text-2xl font-black">{title}</h1>
        <p className="mt-3 text-slate-300">
          {message ||
            "This event area is not currently available for your account. It may not have started yet, may have ended, or may require a different event assignment."}
        </p>
        <Link
          className="mt-6 inline-flex rounded-xl bg-yellow-400 px-5 py-3 font-black text-slate-950"
          href="/events/entry"
        >
          Return to event home
        </Link>
      </section>
    </main>
  );
}
