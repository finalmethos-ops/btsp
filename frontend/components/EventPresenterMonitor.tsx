"use client";

import { useEffect, useState } from "react";
import {
  downloadPublicPresenterImage,
  EventPresentation,
  getPublicEventPresenterPresentation,
} from "@/lib/event-presentation-api";

const formatMoney = (value: string | number | null | undefined) =>
  Number(value ?? 0).toLocaleString(undefined, {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });

export function EventPresenterMonitor({
  presenterToken,
  subEventId,
}: {
  presenterToken: string;
  subEventId: string;
}) {
  const [presentation, setPresentation] = useState<EventPresentation | null>(
    null,
  );
  const [imageUrl, setImageUrl] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    let refreshing = false;
    const refresh = () => {
      if (refreshing) return;
      refreshing = true;
      void getPublicEventPresenterPresentation(subEventId, presenterToken)
        .then((nextPresentation) => {
          if (!active) return;
          setPresentation(nextPresentation);
          setError(null);
        })
        .catch((caught: unknown) => {
          if (!active) return;
          setError(
            caught instanceof Error
              ? caught.message
              : "Unable to load the presenter monitor.",
          );
        })
        .finally(() => {
          refreshing = false;
        });
    };
    refresh();
    const timer = window.setInterval(refresh, 1_000);
    return () => {
      active = false;
      window.clearInterval(timer);
    };
  }, [presenterToken, subEventId]);

  const orderedSlides = [...(presentation?.presenter_slides ?? [])].sort(
    (left, right) => left.position - right.position,
  );
  const currentSlide = presentation?.current_slide ?? null;
  const nextSlide =
    presentation?.current_position == null
      ? (orderedSlides[0] ?? null)
      : (orderedSlides.find(
          (slide) => slide.position > (presentation.current_position ?? 0),
        ) ?? null);
  const currentProducts = currentSlide
    ? currentSlide.product_variants.length
      ? currentSlide.product_variants
      : currentSlide.slide_type === "product"
        ? [
            {
              model_number: currentSlide.model_number ?? "",
              name: currentSlide.name,
              event_unit_cost: currentSlide.event_unit_cost ?? "0.00",
              standard_cost: currentSlide.standard_cost,
              minimum_order_quantity: currentSlide.minimum_order_quantity,
            },
          ]
        : []
    : [];
  const offerLimit =
    currentSlide?.max_event_units ?? currentSlide?.available_inventory;
  const unitsRemaining =
    offerLimit == null
      ? null
      : Math.max(offerLimit - (presentation?.total_units_ordered ?? 0), 0);

  useEffect(() => {
    let active = true;
    let objectUrl: string | null = null;
    setImageUrl(null);
    if (nextSlide?.has_image)
      void downloadPublicPresenterImage(
        subEventId,
        nextSlide.id,
        presenterToken,
      )
        .then((blob) => {
          objectUrl = URL.createObjectURL(blob);
          if (active) setImageUrl(objectUrl);
        })
        .catch(() => undefined);
    return () => {
      active = false;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [nextSlide?.has_image, nextSlide?.id, presenterToken, subEventId]);

  return (
    <main className="presenter-monitor min-h-[calc(100dvh-5rem)] bg-slate-950 p-4 text-white sm:p-6">
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
        <div className="grid grid-cols-2 gap-2 text-center sm:grid-cols-3">
          <div className="rounded-xl border border-slate-700 bg-slate-900 px-4 py-2">
            <span className="block text-[0.65rem] font-black uppercase tracking-wider text-slate-400">
              Slide
            </span>
            <strong>
              {presentation?.current_position ?? 0} /{" "}
              {presentation?.total_slides ?? 0}
            </strong>
          </div>
          <div className="rounded-xl border border-slate-700 bg-slate-900 px-4 py-2">
            <span className="block text-[0.65rem] font-black uppercase tracking-wider text-slate-400">
              Ordering
            </span>
            <strong
              className={
                presentation?.ordering_status === "open"
                  ? "text-green-400"
                  : "text-slate-200"
              }
            >
              {presentation?.ordering_status ?? "closed"}
            </strong>
          </div>
          <div className="col-span-2 rounded-xl border border-slate-700 bg-slate-900 px-4 py-2 sm:col-span-1">
            <span className="block text-[0.65rem] font-black uppercase tracking-wider text-slate-400">
              Show status
            </span>
            <strong>{presentation?.status ?? "idle"}</strong>
          </div>
        </div>
      </header>

      {error ? (
        <p className="mt-4 rounded-xl border border-red-400 bg-red-950 p-3 text-red-100">
          {error}
        </p>
      ) : null}

      <section className="mt-5 grid min-h-0 gap-5 lg:h-[calc(100dvh-10.75rem)] lg:grid-cols-2">
        <article className="min-h-0 overflow-y-auto rounded-2xl border-2 border-amber-300/70 bg-slate-900/90 p-5">
          <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-700 pb-3">
            <div>
              <p className="text-sm font-black uppercase tracking-[0.22em] text-amber-300">
                Current Slide
              </p>
              <p className="mt-1 text-sm text-slate-400">
                Live offer and confirmed order activity
              </p>
            </div>
            {currentSlide ? (
              <span className="rounded-full bg-amber-300 px-3 py-1 text-xs font-black text-slate-950">
                SLIDE {currentSlide.position}
              </span>
            ) : null}
          </div>

          {currentSlide ? (
            <div className="mt-4">
              <h2 className="text-3xl font-black leading-tight">
                {currentSlide.name}
              </h2>
              <div className="mt-2 flex flex-wrap gap-x-6 gap-y-1 text-sm uppercase tracking-wide text-slate-400">
                <span>
                  Vendor:{" "}
                  <strong className="text-amber-300">
                    {currentSlide.vendor_name ??
                      currentSlide.vendor_code ??
                      "Event content"}
                  </strong>
                </span>
                {currentSlide.category ? (
                  <span>
                    Category:{" "}
                    <strong className="text-slate-200">
                      {currentSlide.category}
                    </strong>
                  </span>
                ) : null}
              </div>

              {currentSlide.slide_type === "product" ? (
                <>
                  <div className="mt-5 grid gap-3 sm:grid-cols-3">
                    <div className="rounded-xl border border-blue-400/40 bg-blue-950/70 p-4">
                      <span className="text-xs font-black uppercase tracking-wider text-blue-200">
                        Units ordered
                      </span>
                      <strong className="mt-1 block text-3xl">
                        {(
                          presentation?.total_units_ordered ?? 0
                        ).toLocaleString()}
                      </strong>
                    </div>
                    <div className="rounded-xl border border-green-400/40 bg-green-950/50 p-4">
                      <span className="text-xs font-black uppercase tracking-wider text-green-200">
                        Remaining stock
                      </span>
                      <strong className="mt-1 block text-3xl text-green-300">
                        {unitsRemaining?.toLocaleString() ?? "Unlimited"}
                      </strong>
                    </div>
                    <div className="rounded-xl border border-amber-300/50 bg-amber-950/50 p-4">
                      <span className="text-xs font-black uppercase tracking-wider text-amber-200">
                        Current order total
                      </span>
                      <strong className="mt-1 block text-3xl text-amber-300">
                        ${formatMoney(presentation?.total_combined_spend)}
                      </strong>
                    </div>
                  </div>

                  <section className="mt-5">
                    <h3 className="text-xs font-black uppercase tracking-[0.18em] text-slate-400">
                      Product details
                    </h3>
                    <div className="mt-2 grid gap-2 sm:grid-cols-2">
                      {currentProducts.map((product) => (
                        <div
                          className="rounded-xl border border-slate-700 bg-slate-950/70 p-3"
                          key={product.model_number}
                        >
                          <strong className="line-clamp-2 block text-base">
                            {product.name}
                          </strong>
                          <div className="mt-1 flex items-end justify-between gap-3">
                            <span className="text-sm text-slate-400">
                              {product.model_number}
                            </span>
                            <span className="shrink-0 text-lg font-black text-amber-300">
                              ${formatMoney(product.event_unit_cost)} / EA
                            </span>
                          </div>
                          {currentSlide.product_variants.length ? (
                            <span className="mt-2 block text-sm font-bold text-green-300">
                              {presentation?.variant_units_ordered?.[
                                product.model_number
                              ] ?? 0}{" "}
                              sold
                            </span>
                          ) : null}
                        </div>
                      ))}
                    </div>
                  </section>
                </>
              ) : (
                <div className="mt-5 rounded-xl border border-slate-700 bg-slate-950/70 p-4">
                  <span className="text-xs font-black uppercase tracking-wider text-amber-300">
                    {currentSlide.filler_category?.replaceAll("_", " ") ??
                      "Event content"}
                  </span>
                  <p className="mt-2 text-lg leading-relaxed text-slate-200">
                    {currentSlide.description ??
                      "No ordering is expected for this slide."}
                  </p>
                </div>
              )}

              {presentation?.presenter_notes ? (
                <aside className="mt-5 rounded-xl border border-amber-300/60 bg-amber-950/50 p-4">
                  <span className="text-xs font-black uppercase tracking-[0.18em] text-amber-300">
                    Presenter notes
                  </span>
                  <p className="mt-2 whitespace-pre-line text-base leading-relaxed text-amber-50">
                    {presentation.presenter_notes}
                  </p>
                </aside>
              ) : null}
            </div>
          ) : (
            <div className="flex min-h-72 items-center justify-center text-center">
              <div>
                <p className="text-2xl font-black">Presentation not started</p>
                <p className="mt-2 text-slate-400">
                  Current-slide details will appear when the controller starts
                  the show.
                </p>
              </div>
            </div>
          )}
        </article>

        <article className="flex min-h-0 flex-col overflow-hidden rounded-2xl border border-slate-700 bg-slate-900/90 p-5">
          <div className="flex items-center justify-between gap-3 border-b border-slate-700 pb-3">
            <div>
              <p className="text-sm font-black uppercase tracking-[0.22em] text-blue-300">
                Next Slide
              </p>
              <p className="mt-1 text-sm text-slate-400">
                Prepare the upcoming product or event content
              </p>
            </div>
            {nextSlide ? (
              <span className="rounded-full bg-blue-300 px-3 py-1 text-xs font-black text-slate-950">
                SLIDE {nextSlide.position}
              </span>
            ) : null}
          </div>

          {nextSlide ? (
            <>
              <div className="presenter-monitor-image mt-4 flex min-h-64 flex-1 items-center justify-center overflow-hidden rounded-xl border border-slate-700 bg-slate-950/80">
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
              <div className="pt-4">
                <h2 className="text-3xl font-black leading-tight">
                  {nextSlide.name}
                </h2>
                <div className="mt-2 flex flex-wrap gap-x-6 gap-y-1 text-base text-slate-300">
                  {nextSlide.model_number ? (
                    <span>Model {nextSlide.model_number}</span>
                  ) : null}
                  <span>
                    Vendor:{" "}
                    <strong className="text-blue-300">
                      {nextSlide.vendor_name ??
                        nextSlide.vendor_code ??
                        nextSlide.filler_category?.replaceAll("_", " ") ??
                        "Event content"}
                    </strong>
                  </span>
                </div>
              </div>
            </>
          ) : (
            <div className="flex min-h-72 flex-1 items-center justify-center text-center">
              <div>
                <p className="text-2xl font-black">No slide is queued next</p>
                <p className="mt-2 text-slate-400">
                  The presentation is on its final slide or has ended.
                </p>
              </div>
            </div>
          )}
        </article>
      </section>
    </main>
  );
}
