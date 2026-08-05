"use client";

import { useEffect, useState } from "react";
import {
  downloadPresentationImage,
  EventPresentation,
  getEventPresentation,
} from "@/lib/event-presentation-api";
import { EventAccessUnavailable } from "@/components/EventAccessUnavailable";
import { useEventBrandAsset } from "@/components/EventBrandingProvider";
import { subscribeEventRealtime } from "@/lib/event-realtime";

const IMAGE_FIT_STORAGE_KEY = "btsp.presentation.image-fit";

export function EventPresentationDisplay({
  subEventId,
}: {
  subEventId: string;
}) {
  const [presentation, setPresentation] = useState<EventPresentation | null>(
    null,
  );
  const [error, setError] = useState<string | null>(null);
  const [imageUrl, setImageUrl] = useState<string | null>(null);
  const [imageFit, setImageFit] = useState<"contain" | "cover">("contain");
  const slide = presentation?.current_slide;
  const isFiller = slide?.slide_type === "filler";
  const slideId = slide?.id;
  const slideHasImage = slide?.has_image;
  const eventBranding = useEventBrandAsset(presentation?.event_id);
  const offerLimit = slide?.max_event_units ?? slide?.available_inventory;
  const unitsRemaining =
    offerLimit == null
      ? null
      : Math.max(offerLimit - (presentation?.total_units_ordered ?? 0), 0);

  useEffect(() => {
    const apply = () => {
      const value = window.localStorage.getItem(IMAGE_FIT_STORAGE_KEY);
      if (value === "contain" || value === "cover") setImageFit(value);
    };
    apply();
    window.addEventListener("storage", apply);
    return () => window.removeEventListener("storage", apply);
  }, []);

  useEffect(() => {
    let active = true;
    const refresh = () =>
      void getEventPresentation(subEventId)
        .then((value) => {
          if (active) {
            setPresentation(value);
            setError(null);
          }
        })
        .catch((caught: unknown) => {
          if (active)
            setError(
              caught instanceof Error
                ? caught.message
                : "Unable to load the presentation.",
            );
        });
    refresh();
    const timer = window.setInterval(refresh, 15_000);
    const unsubscribe = subscribeEventRealtime(subEventId, refresh);
    return () => {
      active = false;
      window.clearInterval(timer);
      unsubscribe();
    };
  }, [subEventId]);

  useEffect(() => {
    let url: string | null = null;
    setImageUrl(null);
    if (slideId && slideHasImage)
      void downloadPresentationImage(slideId)
        .then((blob) => {
          url = URL.createObjectURL(blob);
          setImageUrl(url);
        })
        .catch(() => undefined);
    return () => {
      if (url) URL.revokeObjectURL(url);
    };
  }, [slideHasImage, slideId]);

  if (!presentation && error)
    return (
      <EventAccessUnavailable
        message={error}
        title="Presentation unavailable"
      />
    );

  return (
    <main
      className={eventBranding.brandedClassName(
        "event-ui event-presentation-display flex min-h-screen flex-col bg-slate-950 p-4 text-white sm:p-8",
      )}
      style={eventBranding.brandedStyle()}
    >
      <header className="flex justify-between border-b border-slate-700 pb-4">
        <div>
          <p className="text-blue-300">{presentation?.event_name}</p>
          <h1 className="text-3xl font-bold">
            {presentation?.sub_event_name ?? "Live Buying Event"}
          </h1>
        </div>
        <strong
          className={
            presentation?.ordering_status === "open"
              ? "text-green-400"
              : "text-amber-400"
          }
        >
          {isFiller
            ? slide?.filler_category?.replaceAll("_", " ").toUpperCase()
            : presentation?.ordering_status === "open"
              ? "ORDERING OPEN"
              : "ORDERING CLOSED"}
        </strong>
      </header>
      {slide ? (
        slide.slide_type === "filler" ? (
          <section className="flex flex-1 flex-col items-center justify-center gap-8 py-10 text-center">
            <span className="rounded-full border border-blue-400/40 bg-blue-950 px-5 py-2 text-sm font-black uppercase tracking-[0.2em] text-blue-200">
              {slide.filler_category?.replaceAll("_", " ")}
            </span>
            {imageUrl ? (
              // Authenticated blob URL cannot use the Next image optimizer.
              // eslint-disable-next-line @next/next/no-img-element
              <img
                alt={slide.name}
                className={`max-h-[55vh] max-w-5xl rounded-3xl ${imageFit === "contain" ? "object-contain" : "object-cover"}`}
                src={imageUrl}
              />
            ) : null}
            <div className="max-w-5xl">
              <h2 className="text-5xl font-black sm:text-7xl">{slide.name}</h2>
              {slide.description ? (
                <p className="mt-6 whitespace-pre-line text-2xl leading-relaxed text-slate-200 sm:text-3xl">
                  {slide.description}
                </p>
              ) : null}
            </div>
            {eventBranding.brandingUrl ? (
              // Authenticated event-brand blob URL.
              // eslint-disable-next-line @next/next/no-img-element
              <img
                alt={`${presentation?.event_name ?? "Event"} branding`}
                className="mt-4 max-h-24 max-w-64 object-contain"
                src={eventBranding.brandingUrl}
              />
            ) : null}
          </section>
        ) : (
          <>
            <div className="grid flex-1 items-stretch gap-6 py-8 lg:grid-cols-[minmax(0,1.15fr)_minmax(0,1fr)_minmax(18rem,0.72fr)]">
              {imageUrl ? (
                // Authenticated blob URLs cannot use the Next image optimizer.
                // eslint-disable-next-line @next/next/no-img-element
                <img
                  alt={slide.name}
                  className={`max-h-[60vh] w-full rounded-2xl bg-white ${imageFit === "contain" ? "object-contain" : "object-cover"}`}
                  src={imageUrl}
                />
              ) : (
                <div className="flex min-h-80 items-center justify-center rounded-2xl bg-slate-900 text-slate-500">
                  Product image
                </div>
              )}
              <div className="flex flex-col justify-center">
                <h2 className="text-3xl font-black sm:text-4xl xl:text-5xl">
                  {slide.name}
                </h2>
                <p className="mt-2 text-xl text-slate-300 xl:text-2xl">
                  {slide.model_number}
                </p>
                <div className="mt-5 flex flex-wrap gap-x-8 gap-y-2 border-y border-slate-700 py-3 text-sm uppercase tracking-wide">
                  <span className="text-slate-400">
                    Vendor:{" "}
                    <strong className="text-blue-300">
                      {slide.vendor_name ?? slide.vendor_code}
                    </strong>
                  </span>
                  <span className="text-slate-400">
                    Category:{" "}
                    <strong className="text-blue-300">
                      {slide.category ?? "General merchandise"}
                    </strong>
                  </span>
                </div>
                <p className="mt-5 text-xs font-bold uppercase tracking-widest text-slate-400">
                  Description
                </p>
                <p className="mt-2 text-base leading-relaxed text-slate-200 xl:text-lg">
                  {slide.description || "Offer description pending."}
                </p>
                {slide.specifications ? (
                  <p className="mt-3 text-sm text-slate-400">
                    {slide.specifications}
                  </p>
                ) : null}
                <div className="mt-6">
                  <p className="text-sm font-black uppercase tracking-widest text-red-400">
                    Event price
                  </p>
                  <strong className="text-4xl font-black text-red-400 xl:text-5xl">
                    $
                    {Number(slide.event_unit_cost).toLocaleString(undefined, {
                      minimumFractionDigits: 2,
                      maximumFractionDigits: 2,
                    })}
                    <small className="ml-2 text-xl">/ EA</small>
                  </strong>
                </div>
                {slide.product_variants.length ? (
                  <div className="mt-5 flex flex-wrap gap-2">
                    {slide.product_variants.map((variant) => (
                      <span
                        className="rounded-full border border-blue-400/40 bg-blue-950 px-3 py-1 text-sm"
                        key={variant.model_number}
                      >
                        {variant.name} · ${variant.event_unit_cost}
                      </span>
                    ))}
                  </div>
                ) : null}
              </div>
              <aside className="overflow-hidden rounded-2xl border border-slate-700 bg-slate-900/85">
                <h3 className="border-b border-slate-700 px-5 py-4 text-center text-sm font-black uppercase tracking-[0.18em]">
                  Offer Details
                </h3>
                <dl className="divide-y divide-slate-700 text-sm">
                  <div className="flex justify-between gap-4 px-5 py-4">
                    <dt className="font-bold uppercase text-slate-400">
                      Max available units
                    </dt>
                    <dd className="font-black">
                      {offerLimit?.toLocaleString() ?? "Unlimited"} EA
                    </dd>
                  </div>
                  <div className="flex justify-between gap-4 px-5 py-4">
                    <dt className="font-bold uppercase text-slate-400">
                      Units ordered
                    </dt>
                    <dd className="font-black">
                      {(
                        presentation?.total_units_ordered ?? 0
                      ).toLocaleString()}{" "}
                      EA
                    </dd>
                  </div>
                  <div className="flex justify-between gap-4 px-5 py-4">
                    <dt className="font-bold uppercase text-slate-400">
                      Units remaining
                    </dt>
                    <dd className="font-black text-green-400">
                      {unitsRemaining?.toLocaleString() ?? "Unlimited"} EA
                    </dd>
                  </div>
                  <div className="px-5 py-4">
                    <div className="flex items-center justify-between gap-4">
                      <dt className="font-bold uppercase text-slate-400">
                        Ordering window
                      </dt>
                      <dd
                        className={`rounded-full px-3 py-1 text-xs font-black uppercase ${presentation?.ordering_status === "open" ? "bg-green-600 text-white" : "bg-slate-700 text-slate-200"}`}
                      >
                        {presentation?.ordering_status ?? "closed"}
                      </dd>
                    </div>
                    <div className="mt-3 font-black">
                      Controlled by presenter
                    </div>
                  </div>
                  <div className="px-5 py-4">
                    <dt className="font-bold uppercase text-slate-400">
                      Delivery window
                    </dt>
                    <dd className="mt-2 font-black">
                      {slide.delivery_window_start && slide.delivery_window_end
                        ? `${new Date(`${slide.delivery_window_start}T00:00:00`).toLocaleDateString()} — ${new Date(`${slide.delivery_window_end}T00:00:00`).toLocaleDateString()}`
                        : "To be confirmed"}
                    </dd>
                    {slide.vendor_delivery_notes ? (
                      <p className="mt-2 text-xs text-slate-400">
                        {slide.vendor_delivery_notes}
                      </p>
                    ) : null}
                  </div>
                  <div className="flex justify-between gap-4 px-5 py-4">
                    <dt className="font-bold uppercase text-slate-400">
                      Minimum order
                    </dt>
                    <dd className="font-black">
                      {slide.minimum_order_quantity} EA
                    </dd>
                  </div>
                </dl>
              </aside>
            </div>
            <section
              className={`grid items-center gap-4 rounded-2xl border p-4 sm:grid-cols-[1fr_auto_1fr] sm:p-6 ${presentation?.ordering_status === "open" ? "border-green-500/70 bg-green-950/30" : "border-slate-700 bg-slate-900/80"}`}
            >
              <div className="text-center sm:text-left">
                <span className="text-sm font-bold uppercase text-slate-400">
                  Live current-product units
                </span>
                <strong className="block text-4xl sm:text-5xl">
                  {presentation?.total_units_ordered ?? 0}
                </strong>
                <small className="text-slate-400">
                  {presentation?.sub_event_units_ordered ?? 0} units across{" "}
                  {presentation?.sub_event_name ?? "this event"}
                </small>
              </div>
              <div className="flex min-w-48 flex-col items-center text-center">
                {eventBranding.brandingUrl ? (
                  // Authenticated event-brand blob URL.
                  // eslint-disable-next-line @next/next/no-img-element
                  <img
                    alt={`${presentation?.event_name ?? "Event"} branding`}
                    className="mb-2 max-h-20 max-w-48 object-contain"
                    src={eventBranding.brandingUrl}
                  />
                ) : (
                  <strong className="text-xl">
                    {presentation?.event_name}
                  </strong>
                )}
                <span
                  className={`font-black tracking-widest ${presentation?.ordering_status === "open" ? "text-green-400" : "text-amber-300"}`}
                >
                  {presentation?.ordering_status === "open"
                    ? "● ORDERS ARE LIVE"
                    : "ORDERING CLOSED"}
                </span>
                {presentation?.ordering_status === "open" ? (
                  <small>Presenter closes ordering</small>
                ) : null}
              </div>
              <div className="text-center sm:text-right">
                <span className="text-sm font-bold uppercase text-slate-400">
                  Live current-product spend
                </span>
                <strong className="block text-4xl sm:text-5xl">
                  ${presentation?.total_combined_spend ?? "0.00"}
                </strong>
                <small className="text-slate-400">
                  ${presentation?.sub_event_combined_spend ?? "0.00"} across{" "}
                  {presentation?.sub_event_name ?? "this event"}
                </small>
              </div>
            </section>
          </>
        )
      ) : (
        <div className="flex flex-1 items-center justify-center text-4xl text-slate-500">
          Waiting for the presenter to start…
        </div>
      )}
    </main>
  );
}
