"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { ManagedSubEvent } from "@/lib/event-admin-api";
import {
  controlEventPresentation,
  createEventPresenterAccess,
  createEventProjectorAccess,
  EventLiveAnalytics,
  EventPresentation,
  getEventLiveAnalytics,
  getEventPresenterPresentation,
  PresentationAction,
} from "@/lib/event-presentation-api";
import { subscribeEventRealtime } from "@/lib/event-realtime";

const IMAGE_FIT_STORAGE_KEY = "btsp.presentation.image-fit";

export function EventPresenterConsole({
  subEvents,
}: {
  subEvents: ManagedSubEvent[];
}) {
  const [subEventId, setSubEventId] = useState(subEvents[0]?.id ?? "");
  const [presentation, setPresentation] = useState<EventPresentation | null>(
    null,
  );
  const [analytics, setAnalytics] = useState<EventLiveAnalytics | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [imageFit, setImageFit] = useState<"contain" | "cover">("contain");
  const [projectorToken, setProjectorToken] = useState<string | null>(null);
  const [projectorLinkError, setProjectorLinkError] = useState(false);
  const [presenterToken, setPresenterToken] = useState<string | null>(null);
  const [presenterLinkError, setPresenterLinkError] = useState(false);

  useEffect(() => {
    const saved = window.localStorage.getItem(IMAGE_FIT_STORAGE_KEY);
    if (saved === "contain" || saved === "cover") setImageFit(saved);
  }, []);

  function changeImageFit(value: "contain" | "cover") {
    setImageFit(value);
    window.localStorage.setItem(IMAGE_FIT_STORAGE_KEY, value);
  }

  useEffect(() => {
    if (!subEvents.some((item) => item.id === subEventId))
      setSubEventId(subEvents[0]?.id ?? "");
  }, [subEventId, subEvents]);

  useEffect(() => {
    if (!subEventId) return;
    const refresh = () => {
      void getEventPresenterPresentation(subEventId)
        .then(setPresentation)
        .catch(() => setPresentation(null));
      void getEventLiveAnalytics(subEventId)
        .then(setAnalytics)
        .catch(() => setAnalytics(null));
    };
    refresh();
    const timer = window.setInterval(refresh, 15_000);
    const unsubscribe = subscribeEventRealtime(subEventId, refresh);
    return () => {
      window.clearInterval(timer);
      unsubscribe();
    };
  }, [subEventId]);

  useEffect(() => {
    let active = true;
    setProjectorToken(null);
    setProjectorLinkError(false);
    setPresenterToken(null);
    setPresenterLinkError(false);
    if (!subEventId) return;
    void createEventProjectorAccess(subEventId)
      .then((access) => {
        if (active) setProjectorToken(access.projector_token);
      })
      .catch(() => {
        if (active) setProjectorLinkError(true);
      });
    void createEventPresenterAccess(subEventId)
      .then((access) => {
        if (active) setPresenterToken(access.presenter_token);
      })
      .catch(() => {
        if (active) setPresenterLinkError(true);
      });
    return () => {
      active = false;
    };
  }, [subEventId]);

  async function control(action: PresentationAction) {
    setBusy(true);
    setError(null);
    try {
      setPresentation(await controlEventPresentation(subEventId, action));
    } catch (caught) {
      setError(
        caught instanceof Error
          ? caught.message
          : "Presentation control failed",
      );
    } finally {
      setBusy(false);
    }
  }

  const isLive = presentation?.status === "live";
  const isProductSlide = presentation?.current_slide?.slide_type === "product";
  const visibleQueue = (presentation?.slide_queue ?? [])
    .filter(
      (slide) =>
        presentation?.current_position == null ||
        slide.position >= presentation.current_position,
    )
    .slice(0, 6);

  useEffect(() => {
    const keydown = (event: KeyboardEvent) => {
      if (!isLive) return;
      if ((event.target as HTMLElement)?.matches("input, textarea, select"))
        return;
      if (event.key === "ArrowRight") void control("next");
      if (event.key === "ArrowLeft") void control("previous");
      if (event.key === " ") {
        event.preventDefault();
        if (isProductSlide) void control("open");
      }
      if (event.key === "Enter") void control("close");
    };
    window.addEventListener("keydown", keydown);
    return () => window.removeEventListener("keydown", keydown);
  });

  if (!subEvents.length) return null;
  return (
    <section className="event-ui rounded-2xl border bg-slate-950 p-5 text-white">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="text-xs font-bold uppercase tracking-wide text-blue-300">
            020C · Presenter console
          </p>
          <h3 className="text-xl font-bold">Live presentation control</h3>
        </div>
        <select
          className="rounded-lg border border-slate-600 bg-slate-900 p-2"
          onChange={(event) => setSubEventId(event.target.value)}
          value={subEventId}
        >
          {subEvents.map((item) => (
            <option key={item.id} value={item.id}>
              {item.name}
            </option>
          ))}
        </select>
        <label className="flex items-center gap-2 text-sm text-slate-300">
          Image fit
          <select
            aria-label="Presentation image fit"
            className="rounded-lg border border-slate-600 bg-slate-900 p-2"
            onChange={(event) =>
              changeImageFit(event.target.value as "contain" | "cover")
            }
            value={imageFit}
          >
            <option value="contain">Contain (preserve ratio)</option>
            <option value="cover">Cover (crop edges)</option>
          </select>
        </label>
      </div>
      <div className="mt-3 grid gap-3 sm:grid-cols-4">
        <div className="presenter-console-card rounded-xl bg-slate-900 p-3">
          <span className="text-xs text-slate-400">RESPONDED</span>
          <strong className="block text-2xl">
            {analytics?.responding_entities ?? 0}/
            {analytics?.assigned_entities ?? 0}
          </strong>
        </div>
        <div className="presenter-console-card rounded-xl bg-slate-900 p-3">
          <span className="text-xs text-slate-400">REMAINING</span>
          <strong className="block text-2xl">
            {analytics?.entities_remaining ?? 0}
          </strong>
        </div>
        <div className="presenter-console-card rounded-xl bg-slate-900 p-3">
          <span className="text-xs text-slate-400">CONFIRMED</span>
          <strong className="block text-2xl">
            {analytics?.confirmed_units ?? 0} units
          </strong>
        </div>
        <div className="presenter-console-card rounded-xl bg-slate-900 p-3">
          <span className="text-xs text-slate-400">WAITLIST</span>
          <strong className="block text-2xl">
            {analytics?.waitlisted_units ?? 0} units
          </strong>
        </div>
      </div>
      <div className="mt-3 grid gap-3 sm:grid-cols-2">
        <div className="presenter-console-card rounded-xl bg-slate-900 p-3">
          <span className="text-xs text-slate-400">CURRENT PRODUCT SPEND</span>
          <strong className="block text-2xl">
            ${presentation?.total_combined_spend ?? "0.00"}
          </strong>
        </div>
        <div className="presenter-console-card rounded-xl bg-slate-900 p-3">
          <span className="text-xs text-slate-400">
            {presentation?.sub_event_name ?? "Current event"} spend
          </span>
          <strong className="block text-2xl">
            ${presentation?.sub_event_combined_spend ?? "0.00"}
          </strong>
        </div>
      </div>
      {error ? (
        <p className="mt-3 rounded-lg bg-red-950 p-2 text-red-200">{error}</p>
      ) : null}
      <div className="mt-4 grid gap-3 sm:grid-cols-3">
        <div className="presenter-console-card rounded-xl bg-slate-900 p-3">
          <span className="text-xs text-slate-400">STATUS</span>
          <strong className="block text-lg uppercase">
            {presentation?.status ?? "idle"}
          </strong>
        </div>
        <div className="presenter-console-card rounded-xl bg-slate-900 p-3">
          <span className="text-xs text-slate-400">CURRENT SLIDE</span>
          <strong className="block text-lg">
            {presentation?.current_position ?? "—"} /{" "}
            {presentation?.total_slides ?? 0}
          </strong>
        </div>
        <div
          className={`rounded-xl p-3 ${presentation?.ordering_status === "open" ? "bg-green-800" : "presenter-console-card bg-slate-900"}`}
        >
          <span className="text-xs text-slate-300">ORDERING</span>
          <strong className="block text-lg uppercase">
            {presentation?.ordering_status ?? "closed"}
          </strong>
          {presentation?.ordering_status === "open" ? (
            <small className="block">Controlled by the presenter</small>
          ) : null}
        </div>
      </div>
      <p className="mt-4 text-lg font-semibold">
        {presentation?.current_slide
          ? presentation.current_slide.slide_type === "filler"
            ? `${presentation.current_slide.filler_category?.replaceAll("_", " ")} — ${presentation.current_slide.name}`
            : `${presentation.current_slide.model_number} — ${presentation.current_slide.name}`
          : "No active slide"}
      </p>
      {presentation?.presenter_notes ? (
        <aside className="mt-3 rounded-xl border border-amber-400/50 bg-amber-950/40 p-3">
          <span className="text-xs font-black uppercase tracking-wide text-amber-300">
            Private presenter notes
          </span>
          <p className="mt-1 whitespace-pre-line text-sm text-amber-50">
            {presentation.presenter_notes}
          </p>
        </aside>
      ) : null}
      {visibleQueue.length ? (
        <div className="mt-4">
          <h4 className="text-xs font-black uppercase tracking-wide text-slate-400">
            Current and upcoming slides
          </h4>
          <ol className="mt-2 grid gap-2 sm:grid-cols-2 xl:grid-cols-3">
            {visibleQueue.map((slide) => {
              const current = slide.id === presentation?.current_slide?.id;
              return (
                <li
                  className={`presenter-queue-card rounded-xl border p-3 ${current ? "is-current" : "is-upcoming"}`}
                  key={slide.id}
                >
                  <span className="text-xs font-bold text-slate-400">
                    {current ? "NOW" : `SLIDE ${slide.position}`}
                  </span>
                  <strong className="block text-sm">
                    {slide.slide_type === "filler"
                      ? slide.filler_category?.replaceAll("_", " ")
                      : slide.model_number}
                  </strong>
                  <span className="block text-sm text-slate-300">
                    {slide.name}
                  </span>
                  {slide.presenter_notes && !current ? (
                    <small className="mt-1 block line-clamp-2 text-amber-200">
                      {slide.presenter_notes}
                    </small>
                  ) : null}
                </li>
              );
            })}
          </ol>
        </div>
      ) : null}
      <div className="mt-4 flex flex-wrap gap-2">
        <button
          className="rounded-lg bg-blue-700 px-4 py-2 font-semibold"
          disabled={busy || isLive}
          onClick={() => void control("start")}
        >
          Start
        </button>
        <button
          className="rounded-lg bg-slate-700 px-4 py-2 font-semibold"
          disabled={busy || !isLive}
          onClick={() => void control("previous")}
        >
          ← Previous
        </button>
        <button
          className="rounded-lg bg-slate-700 px-4 py-2 font-semibold"
          disabled={busy || !isLive}
          onClick={() => void control("next")}
        >
          Next →
        </button>
        <button
          className="rounded-lg bg-green-700 px-4 py-2 font-semibold"
          disabled={busy || !isLive || !isProductSlide}
          onClick={() => void control("open")}
        >
          Open ordering
        </button>
        <button
          className="rounded-lg bg-amber-700 px-4 py-2 font-semibold"
          disabled={busy || !isLive}
          onClick={() => void control("close")}
        >
          Close ordering
        </button>
        <button
          className="rounded-lg bg-red-800 px-4 py-2 font-semibold"
          disabled={busy || !isLive}
          onClick={() => void control("end")}
        >
          End event
        </button>
        {projectorToken ? (
          <Link
            className="rounded-lg border border-white px-4 py-2 font-semibold"
            href={`/events/present/${subEventId}#${new URLSearchParams({ projector_token: projectorToken }).toString()}`}
            rel="noopener noreferrer"
            target="_blank"
          >
            Open projector display ↗
          </Link>
        ) : (
          <button
            className="rounded-lg border border-slate-600 px-4 py-2 font-semibold text-slate-400"
            disabled
          >
            {projectorLinkError
              ? "Projector link unavailable"
              : "Preparing projector link…"}
          </button>
        )}
        {presenterToken ? (
          <Link
            className="rounded-lg border border-amber-300 px-4 py-2 font-semibold text-amber-200"
            href={`/events/presenter/${subEventId}#${new URLSearchParams({ presenter_token: presenterToken }).toString()}`}
            rel="noopener noreferrer"
            target="_blank"
          >
            Open presenter monitor ↗
          </Link>
        ) : (
          <button
            className="rounded-lg border border-slate-600 px-4 py-2 font-semibold text-slate-400"
            disabled
          >
            {presenterLinkError
              ? "Presenter link unavailable"
              : "Preparing presenter link…"}
          </button>
        )}
      </div>
      <p className="mt-3 text-xs text-slate-400">
        Keyboard: ←/→ slides · Space opens product ordering · Enter closes
        ordering. Ordering remains open until the controller closes it or
        changes slides.
      </p>
      <div className="mt-5 grid gap-4 border-t border-slate-700 pt-5 xl:grid-cols-[1.4fr_0.8fr_1fr]">
        <section className="presenter-console-card rounded-xl bg-slate-900 p-4">
          <div className="flex items-center justify-between gap-3">
            <h4 className="font-bold">Live order summary by entity</h4>
            <span className="text-xs text-slate-400">Current product</span>
          </div>
          <div className="mt-3 max-h-64 overflow-auto">
            <table className="w-full text-left text-sm">
              <thead className="sticky top-0 bg-slate-900 text-xs uppercase text-slate-400">
                <tr>
                  <th className="py-2">Entity</th>
                  <th>Qty</th>
                  <th>Spend</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {(analytics?.orders ?? []).map((order) => (
                  <tr
                    className="border-t border-slate-800"
                    key={`${order.entity_code}-${order.updated_at}`}
                  >
                    <td className="py-2 font-semibold">{order.entity_code}</td>
                    <td>{order.quantity}</td>
                    <td>${order.total_cost}</td>
                    <td
                      className={
                        order.status === "confirmed"
                          ? "text-green-400"
                          : "text-amber-300"
                      }
                    >
                      {order.status}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {!analytics?.orders.length ? (
              <p className="py-5 text-center text-sm text-slate-500">
                No orders received for this product yet.
              </p>
            ) : null}
          </div>
        </section>
        <section className="presenter-console-card rounded-xl bg-slate-900 p-4">
          <h4 className="font-bold">Event progress</h4>
          <div className="presenter-progress-dial mt-4 flex aspect-square max-h-44 items-center justify-center rounded-full border-[12px] border-blue-700 bg-slate-950 text-center">
            <strong className="text-3xl">
              {presentation?.current_position ?? 0}
              <small className="block text-sm text-slate-400">
                of {presentation?.total_slides ?? 0}
              </small>
            </strong>
          </div>
          <p className="mt-3 text-sm text-slate-400">
            {Math.max(
              (presentation?.total_slides ?? 0) -
                (presentation?.current_position ?? 0),
              0,
            )}{" "}
            products remaining after the current slide.
          </p>
        </section>
        <section className="presenter-console-card rounded-xl bg-slate-900 p-4">
          <h4 className="font-bold">Recent activity</h4>
          <div className="mt-3 space-y-2">
            {(analytics?.orders ?? []).slice(0, 6).map((order) => (
              <div
                className="border-b border-slate-800 pb-2 text-sm"
                key={`activity-${order.entity_code}-${order.updated_at}`}
              >
                <strong>{order.entity_code}</strong>{" "}
                {order.status === "confirmed" ? "committed" : "waitlisted"}{" "}
                {order.quantity} units
                <time className="block text-xs text-slate-500">
                  {new Date(order.updated_at).toLocaleTimeString()}
                </time>
              </div>
            ))}
            {!analytics?.orders.length ? (
              <p className="text-sm text-slate-500">
                Waiting for live activity…
              </p>
            ) : null}
          </div>
        </section>
      </div>
    </section>
  );
}
