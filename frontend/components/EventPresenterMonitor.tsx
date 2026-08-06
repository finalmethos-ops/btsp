"use client";

import { useEffect, useState } from "react";
import {
  downloadPresentationImage,
  EventPresentation,
  getEventPresenterPresentation,
} from "@/lib/event-presentation-api";
import {
  EventProductSlide,
  listEventProductSlides,
} from "@/lib/event-product-slide-api";
import { subscribeEventRealtime } from "@/lib/event-realtime";

const formatMoney = (value: string | number | null | undefined) =>
  Number(value ?? 0).toLocaleString(undefined, {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });

export function EventPresenterMonitor({ subEventId }: { subEventId: string }) {
  const [presentation, setPresentation] = useState<EventPresentation | null>(
    null,
  );
  const [slides, setSlides] = useState<EventProductSlide[]>([]);
  const [imageUrl, setImageUrl] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    const refresh = () => {
      void Promise.all([
        getEventPresenterPresentation(subEventId),
        listEventProductSlides(subEventId),
      ])
        .then(([nextPresentation, nextSlides]) => {
          if (!active) return;
          setPresentation(nextPresentation);
          setSlides(nextSlides);
          setError(null);
        })
        .catch((caught: unknown) => {
          if (!active) return;
          setError(
            caught instanceof Error
              ? caught.message
              : "Unable to load the presenter monitor.",
          );
        });
    };
    refresh();
    const timer = window.setInterval(refresh, 5_000);
    const unsubscribe = subscribeEventRealtime(subEventId, refresh);
    return () => {
      active = false;
      window.clearInterval(timer);
      unsubscribe();
    };
  }, [subEventId]);

  const orderedSlides = [...slides].sort(
    (left, right) => left.position - right.position,
  );
  const nextSlide =
    presentation?.current_position == null
      ? (orderedSlides[0] ?? null)
      : (orderedSlides.find(
          (slide) => slide.position > (presentation.current_position ?? 0),
        ) ?? null);
  const followingSlides = orderedSlides
    .filter((slide) => nextSlide && slide.position > nextSlide.position)
    .slice(0, 3);

  useEffect(() => {
    let objectUrl: string | null = null;
    setImageUrl(null);
    if (nextSlide?.has_image)
      void downloadPresentationImage(nextSlide.id)
        .then((blob) => {
          objectUrl = URL.createObjectURL(blob);
          setImageUrl(objectUrl);
        })
        .catch(() => undefined);
    return () => {
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [nextSlide?.has_image, nextSlide?.id]);

  return (
    <main className="presenter-monitor min-h-[calc(100dvh-5rem)] bg-slate-950 p-4 text-white sm:p-7">
      <header className="flex flex-wrap items-start justify-between gap-4 border-b border-slate-700 pb-4">
        <div>
          <p className="text-xs font-black uppercase tracking-[0.2em] text-amber-300">
            Private presenter monitor
          </p>
          <h1 className="mt-1 text-3xl font-black">
            {presentation?.sub_event_name ?? "Live presentation"}
          </h1>
          <p className="mt-1 text-slate-300">{presentation?.event_name}</p>
        </div>
        <div className="rounded-xl border border-slate-600 bg-slate-900/80 px-4 py-3 text-right">
          <span className="block text-xs font-bold uppercase text-slate-400">
            Currently showing
          </span>
          <strong className="block text-lg">
            {presentation?.current_slide?.name ?? "Presentation not started"}
          </strong>
          <span className="text-sm text-slate-300">
            Slide {presentation?.current_position ?? 0} of{" "}
            {presentation?.total_slides ?? 0}
          </span>
        </div>
      </header>

      {error ? (
        <p className="mt-4 rounded-xl border border-red-400 bg-red-950 p-3 text-red-100">
          {error}
        </p>
      ) : null}

      {nextSlide ? (
        <section className="mt-5 grid min-h-0 gap-5 lg:grid-cols-[minmax(18rem,0.85fr)_minmax(0,1.4fr)]">
          <div className="presenter-monitor-image flex min-h-72 items-center justify-center overflow-hidden rounded-2xl border border-slate-700 bg-slate-900/80">
            {imageUrl ? (
              // Protected blob URL cannot use the Next image optimizer.
              // eslint-disable-next-line @next/next/no-img-element
              <img
                alt={nextSlide.name}
                className="h-full max-h-[55dvh] w-full object-contain"
                src={imageUrl}
              />
            ) : (
              <span className="text-slate-400">No preview image</span>
            )}
          </div>
          <div className="min-w-0">
            <p className="text-sm font-black uppercase tracking-[0.22em] text-amber-300">
              Next — slide {nextSlide.position}
            </p>
            <h2 className="mt-2 text-4xl font-black leading-tight xl:text-5xl">
              {nextSlide.name}
            </h2>
            <p className="mt-2 text-2xl text-slate-300">
              {nextSlide.slide_type === "filler"
                ? nextSlide.filler_category?.replaceAll("_", " ")
                : nextSlide.model_number}
            </p>
            {nextSlide.presenter_notes ? (
              <aside className="mt-5 rounded-2xl border-2 border-amber-300 bg-amber-950/60 p-5">
                <span className="text-xs font-black uppercase tracking-[0.18em] text-amber-300">
                  Presenter notes
                </span>
                <p className="mt-2 whitespace-pre-line text-xl leading-relaxed text-amber-50">
                  {nextSlide.presenter_notes}
                </p>
              </aside>
            ) : null}
            {nextSlide.slide_type === "product" ? (
              <div className="mt-5 grid gap-3 sm:grid-cols-2">
                {(nextSlide.product_variants.length
                  ? nextSlide.product_variants
                  : [
                      {
                        model_number: nextSlide.model_number ?? "",
                        name: nextSlide.name,
                        event_unit_cost: nextSlide.event_unit_cost ?? "0.00",
                        standard_cost: nextSlide.standard_cost,
                        minimum_order_quantity:
                          nextSlide.minimum_order_quantity,
                      },
                    ]
                ).map((product) => (
                  <article
                    className="rounded-xl border border-blue-400/40 bg-blue-950/70 p-4"
                    key={product.model_number}
                  >
                    <strong className="block text-lg">{product.name}</strong>
                    <span className="text-slate-300">
                      {product.model_number}
                    </span>
                    <span className="mt-2 block text-xl font-black text-amber-300">
                      ${formatMoney(product.event_unit_cost)} / EA
                    </span>
                  </article>
                ))}
              </div>
            ) : null}
          </div>
        </section>
      ) : (
        <section className="flex min-h-[50dvh] items-center justify-center text-center">
          <div>
            <p className="text-3xl font-black">No slide is queued next.</p>
            <p className="mt-2 text-slate-400">
              The presenter is on the final slide or the show has ended.
            </p>
          </div>
        </section>
      )}

      {followingSlides.length ? (
        <section className="mt-6 border-t border-slate-700 pt-4">
          <h3 className="text-xs font-black uppercase tracking-[0.18em] text-slate-400">
            Following later
          </h3>
          <div className="mt-3 grid gap-3 sm:grid-cols-3">
            {followingSlides.map((slide) => (
              <div
                className="rounded-xl border border-slate-700 bg-slate-900/80 p-3"
                key={slide.id}
              >
                <span className="text-xs font-bold text-amber-300">
                  SLIDE {slide.position}
                </span>
                <strong className="mt-1 block">{slide.name}</strong>
                <span className="text-sm text-slate-400">
                  {slide.model_number ??
                    slide.filler_category?.replaceAll("_", " ")}
                </span>
              </div>
            ))}
          </div>
        </section>
      ) : null}
    </main>
  );
}
