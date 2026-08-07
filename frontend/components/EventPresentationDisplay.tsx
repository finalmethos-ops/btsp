"use client";

import { useEffect, useRef, useState } from "react";
import {
  downloadPublicPresentationBranding,
  downloadPublicPresentationImage,
  downloadPublicPresentationVendorLogo,
  EventPresentation,
  getPublicEventPresentation,
} from "@/lib/event-presentation-api";
import { EventAccessUnavailable } from "@/components/EventAccessUnavailable";
import { eventThemeStyle } from "@/components/EventBrandingProvider";

const IMAGE_FIT_STORAGE_KEY = "btsp.presentation.image-fit";

const formatMoney = (value: string | number) =>
  Number(value).toLocaleString(undefined, {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });

const savingsDetails = (
  standardCost: string | null | undefined,
  eventCost: string | null | undefined,
) => {
  if (!standardCost || eventCost == null) return null;
  const standard = Number(standardCost);
  const event = Number(eventCost);
  if (
    !Number.isFinite(standard) ||
    !Number.isFinite(event) ||
    standard <= event
  )
    return null;
  return {
    amount: standard - event,
    percent: Math.round(((standard - event) / standard) * 100),
  };
};

export function EventPresentationDisplay({
  projectorToken,
  subEventId,
}: {
  projectorToken: string;
  subEventId: string;
}) {
  const [presentation, setPresentation] = useState<EventPresentation | null>(
    null,
  );
  const [error, setError] = useState<string | null>(null);
  const [imageUrl, setImageUrl] = useState<string | null>(null);
  const imageCacheRef = useRef(new Map<string, string>());
  const imageDownloadsRef = useRef(new Set<string>());
  const desiredImageIdsRef = useRef(new Set<string>());
  const [brandingUrl, setBrandingUrl] = useState<string | null>(null);
  const [vendorLogoUrl, setVendorLogoUrl] = useState<string | null>(null);
  const [imageFit, setImageFit] = useState<"contain" | "cover">("contain");
  const slide = presentation?.current_slide;
  const isFiller = slide?.slide_type === "filler";
  const isFullScreenImage =
    isFiller && slide?.filler_category === "full_screen_image";
  const isMultiProduct = Boolean(slide?.product_variants.length);
  const slideId = slide?.id;
  const slideHasImage = slide?.has_image;
  const preloadImageKey = (
    presentation?.projector_image_preload_ids ?? []
  ).join("|");
  const brandedStyle = eventThemeStyle(
    presentation
      ? {
          theme_primary_color: presentation.event_theme_primary_color,
          theme_accent_color: presentation.event_theme_accent_color,
        }
      : undefined,
    brandingUrl,
  );
  const offerLimit = slide?.max_event_units ?? slide?.available_inventory;
  const unitsRemaining =
    offerLimit == null
      ? null
      : Math.max(offerLimit - (presentation?.total_units_ordered ?? 0), 0);
  const primarySavings = savingsDetails(
    slide?.standard_cost,
    slide?.event_unit_cost,
  );

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
    let refreshing = false;
    const refresh = () => {
      if (refreshing) return;
      refreshing = true;
      void getPublicEventPresentation(subEventId, projectorToken)
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
        })
        .finally(() => {
          refreshing = false;
        });
    };
    refresh();
    const timer = window.setInterval(refresh, 750);
    return () => {
      active = false;
      window.clearInterval(timer);
    };
  }, [projectorToken, subEventId]);

  useEffect(() => {
    const desiredIds = new Set(
      preloadImageKey ? preloadImageKey.split("|") : [],
    );
    if (slideId && slideHasImage) desiredIds.add(slideId);
    desiredImageIdsRef.current = desiredIds;
    setImageUrl(slideId ? (imageCacheRef.current.get(slideId) ?? null) : null);

    for (const [cachedId, url] of imageCacheRef.current.entries()) {
      if (!desiredIds.has(cachedId)) {
        URL.revokeObjectURL(url);
        imageCacheRef.current.delete(cachedId);
      }
    }
    for (const imageId of desiredIds) {
      if (
        imageCacheRef.current.has(imageId) ||
        imageDownloadsRef.current.has(imageId)
      )
        continue;
      imageDownloadsRef.current.add(imageId);
      void downloadPublicPresentationImage(subEventId, imageId, projectorToken)
        .then((blob) => {
          const url = URL.createObjectURL(blob);
          if (desiredImageIdsRef.current.has(imageId)) {
            imageCacheRef.current.set(imageId, url);
            if (imageId === slideId) setImageUrl(url);
          } else {
            URL.revokeObjectURL(url);
          }
        })
        .catch(() => undefined)
        .finally(() => imageDownloadsRef.current.delete(imageId));
    }
  }, [preloadImageKey, projectorToken, slideHasImage, slideId, subEventId]);

  useEffect(() => {
    const imageCache = imageCacheRef.current;
    const desiredImageIds = desiredImageIdsRef.current;
    return () => {
      for (const url of imageCache.values()) URL.revokeObjectURL(url);
      imageCache.clear();
      desiredImageIds.clear();
    };
  }, []);

  useEffect(() => {
    let active = true;
    let url: string | null = null;
    setVendorLogoUrl(null);
    if (slideId && slide?.has_vendor_logo)
      void downloadPublicPresentationVendorLogo(
        subEventId,
        slideId,
        projectorToken,
      )
        .then((blob) => {
          url = URL.createObjectURL(blob);
          if (active) setVendorLogoUrl(url);
        })
        .catch(() => undefined);
    return () => {
      active = false;
      if (url) URL.revokeObjectURL(url);
    };
  }, [projectorToken, slide?.has_vendor_logo, slideId, subEventId]);

  useEffect(() => {
    let active = true;
    let url: string | null = null;
    setBrandingUrl(null);
    if (presentation?.event_has_branding)
      void downloadPublicPresentationBranding(subEventId, projectorToken)
        .then((blob) => {
          url = URL.createObjectURL(blob);
          if (active) setBrandingUrl(url);
        })
        .catch(() => undefined);
    return () => {
      active = false;
      if (url) URL.revokeObjectURL(url);
    };
  }, [presentation?.event_has_branding, projectorToken, subEventId]);

  if (!presentation && error)
    return (
      <EventAccessUnavailable
        message={error}
        title="Presentation unavailable"
      />
    );

  if (isFullScreenImage)
    return (
      <main className="relative flex h-screen w-screen items-center justify-center overflow-hidden bg-black">
        {error ? (
          <p className="absolute inset-x-4 top-4 z-10 rounded-xl border border-red-400 bg-red-950/95 p-3 text-center font-bold text-red-100">
            {error}
          </p>
        ) : null}
        {imageUrl ? (
          // Protected blob URL cannot use the Next image optimizer.
          // eslint-disable-next-line @next/next/no-img-element
          <img
            alt={slide.name}
            className={`h-full w-full ${imageFit === "contain" ? "object-contain" : "object-cover"}`}
            src={imageUrl}
          />
        ) : (
          <p className="text-lg font-semibold text-slate-400">
            Preparing full-screen slide…
          </p>
        )}
      </main>
    );

  return (
    <main
      className={`event-ui event-presentation-display event-branded-surface flex min-h-screen flex-col bg-slate-950 p-4 text-white ${presentation ? "has-event-theme" : ""} ${brandingUrl ? "has-event-branding-image" : ""}`}
      style={brandedStyle}
    >
      {error ? (
        <p className="mb-4 rounded-xl border border-red-400 bg-red-950/90 p-3 text-center font-bold text-red-100">
          {error}
        </p>
      ) : null}
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
          <section className="event-presentation-filler flex min-h-0 flex-1 flex-col items-center justify-center gap-8 py-10 text-center">
            <span className="rounded-full border border-blue-400/40 bg-blue-950 px-5 py-2 text-sm font-black uppercase tracking-[0.2em] text-blue-200">
              {slide.filler_category?.replaceAll("_", " ")}
            </span>
            {imageUrl ? (
              // Protected blob URL cannot use the Next image optimizer.
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
            {brandingUrl ? (
              // Protected event-brand blob URL.
              // eslint-disable-next-line @next/next/no-img-element
              <img
                alt={`${presentation?.event_name ?? "Event"} branding`}
                className="mt-4 max-h-24 max-w-64 object-contain"
                src={brandingUrl}
              />
            ) : null}
          </section>
        ) : (
          <div className="event-presentation-product-shell">
            <div className="event-presentation-product-grid grid flex-1 items-stretch gap-5 py-5 lg:grid-cols-[minmax(0,1.08fr)_minmax(0,1fr)_minmax(17rem,0.68fr)]">
              {imageUrl ? (
                // Protected blob URLs cannot use the Next image optimizer.
                // eslint-disable-next-line @next/next/no-img-element
                <img
                  alt={slide.name}
                  className={`event-presentation-product-image max-h-[58vh] w-full rounded-2xl bg-white ${imageFit === "contain" ? "object-contain" : "object-cover"}`}
                  src={imageUrl}
                />
              ) : (
                <div className="flex min-h-80 items-center justify-center rounded-2xl bg-slate-900 text-slate-500">
                  Product image
                </div>
              )}
              <div className="event-presentation-product-copy flex min-w-0 flex-col justify-center">
                <h2 className="text-3xl font-black leading-tight sm:text-4xl xl:text-5xl">
                  {slide.name}
                </h2>
                {!isMultiProduct ? (
                  <p className="mt-1 text-xl text-slate-300 xl:text-2xl">
                    {slide.model_number}
                  </p>
                ) : null}
                <div className="mt-3 flex flex-wrap gap-x-8 gap-y-1 border-y border-slate-700 py-2 text-sm uppercase tracking-wide">
                  <span className="text-slate-400">
                    Vendor:{" "}
                    <strong className="text-blue-300">
                      {slide.vendor_name ?? slide.vendor_code}
                    </strong>
                  </span>
                  <span className="text-slate-400">
                    Category:{" "}
                    <strong className="text-blue-300">
                      {slide.category || "Category not set"}
                    </strong>
                  </span>
                </div>
                <p className="mt-3 text-xs font-bold uppercase tracking-widest text-slate-400">
                  Description
                </p>
                <p className="mt-1 line-clamp-3 text-base leading-relaxed text-slate-200 xl:text-lg">
                  {slide.description || "Offer description pending."}
                </p>
                {slide.specifications ? (
                  <p className="mt-2 line-clamp-2 text-sm text-slate-400">
                    {slide.specifications}
                  </p>
                ) : null}
                {isMultiProduct ? (
                  <div className="presentation-variant-grid mt-3 grid min-h-0 flex-1 gap-3 sm:grid-cols-2">
                    {slide.product_variants.map((variant) => {
                      const savings = savingsDetails(
                        variant.standard_cost,
                        variant.event_unit_cost,
                      );
                      const standardCost = Number(variant.standard_cost);
                      const eventCost = Number(variant.event_unit_cost);
                      const priceDifference = eventCost - standardCost;
                      return (
                        <article
                          className="presentation-variant-card flex min-h-0 flex-col justify-between rounded-xl border border-blue-400/50 bg-blue-950/85 p-3"
                          key={variant.model_number}
                        >
                          <div>
                            <strong className="line-clamp-2 block text-base">
                              {variant.name}
                            </strong>
                            <span className="text-sm text-slate-300">
                              {variant.model_number}
                            </span>
                          </div>
                          <div className="mt-2 border-t border-blue-300/25 pt-2">
                            {variant.standard_cost ? (
                              <span className="block text-xs font-bold text-slate-300">
                                Standard ${formatMoney(variant.standard_cost)}
                              </span>
                            ) : null}
                            <strong className="block text-2xl font-black text-amber-300">
                              ${formatMoney(variant.event_unit_cost)} / EA
                            </strong>
                          </div>
                          {savings ? (
                            <div className="presentation-variant-savings mt-2 rounded-lg px-3 py-2">
                              <strong className="block">
                                Save ${formatMoney(savings.amount)} / EA
                              </strong>
                              <span>
                                {savings.percent}% below Standard Cost
                              </span>
                            </div>
                          ) : (
                            <div className="presentation-variant-savings is-neutral mt-2 rounded-lg px-3 py-2">
                              <strong className="block">
                                Pricing comparison
                              </strong>
                              <span>
                                {!Number.isFinite(standardCost) ||
                                !Number.isFinite(eventCost) ||
                                standardCost <= 0
                                  ? "Standard Cost not provided"
                                  : priceDifference === 0
                                    ? "At Standard Cost"
                                    : `$${formatMoney(Math.abs(priceDifference))} above Standard Cost`}
                              </span>
                            </div>
                          )}
                        </article>
                      );
                    })}
                  </div>
                ) : (
                  <>
                    <div className="mt-4">
                      {slide.standard_cost ? (
                        <p className="text-base font-bold text-slate-300">
                          Standard Cost{" "}
                          <span className="text-xl line-through">
                            ${formatMoney(slide.standard_cost)}
                          </span>
                        </p>
                      ) : null}
                      <p className="text-sm font-black uppercase tracking-widest text-red-400">
                        Event price
                      </p>
                      <strong className="text-4xl font-black text-red-400 xl:text-5xl">
                        ${formatMoney(slide.event_unit_cost ?? 0)}
                        <small className="ml-2 text-xl">/ EA</small>
                      </strong>
                    </div>
                    {primarySavings ? (
                      <div className="presentation-savings-card mt-3 rounded-2xl border-2 px-5 py-3">
                        <p className="text-sm font-black uppercase tracking-[0.18em]">
                          Your savings
                        </p>
                        <strong className="presentation-savings-value mt-1 block text-3xl font-black xl:text-4xl">
                          ${formatMoney(primarySavings.amount)} / EA
                        </strong>
                        <span className="text-base font-black">
                          {primarySavings.percent}% below Standard Cost
                        </span>
                      </div>
                    ) : null}
                  </>
                )}
              </div>
              <aside className="event-presentation-offer-details flex flex-col overflow-hidden rounded-2xl border border-slate-700 bg-slate-900/85">
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
                      {isMultiProduct ? "Product options" : "Minimum order"}
                    </dt>
                    <dd className="font-black">
                      {isMultiProduct
                        ? slide.product_variants.length
                        : `${slide.minimum_order_quantity} EA`}
                    </dd>
                  </div>
                </dl>
                {isMultiProduct ? (
                  <section className="presentation-model-sales border-t border-slate-700 px-5 py-4">
                    <h4 className="text-xs font-black uppercase tracking-[0.16em] text-slate-400">
                      Model sales
                    </h4>
                    <ul className="mt-3 space-y-2 text-sm">
                      {slide.product_variants.slice(0, 8).map((variant) => (
                        <li
                          className="flex items-center justify-between gap-3 border-b border-slate-700/70 pb-2"
                          key={`sales-${variant.model_number}`}
                        >
                          <span className="min-w-0 truncate font-bold">
                            {variant.model_number}
                          </span>
                          <strong className="shrink-0 text-amber-300">
                            {presentation?.variant_units_ordered?.[
                              variant.model_number
                            ] ?? 0}{" "}
                            sold
                          </strong>
                        </li>
                      ))}
                    </ul>
                    {slide.product_variants.length > 8 ? (
                      <p className="mt-2 text-xs text-slate-400">
                        +{slide.product_variants.length - 8} additional models
                      </p>
                    ) : null}
                  </section>
                ) : null}
                {vendorLogoUrl ? (
                  <section className="mt-auto flex min-h-20 items-center justify-center border-t border-slate-700 bg-white/95 px-5 py-3">
                    {/* Protected blob URL cannot use the Next image optimizer. */}
                    {/* eslint-disable-next-line @next/next/no-img-element */}
                    <img
                      alt={`${slide.vendor_name ?? slide.vendor_code ?? "Vendor"} logo`}
                      className="max-h-20 max-w-full object-contain"
                      src={vendorLogoUrl}
                    />
                  </section>
                ) : null}
              </aside>
            </div>
            <section
              className={`event-presentation-footer grid items-center gap-4 rounded-2xl border p-3 sm:grid-cols-[1fr_auto_1fr] ${presentation?.ordering_status === "open" ? "border-green-500/70 bg-green-950/30" : "border-slate-700 bg-slate-900/80"}`}
            >
              <div className="text-center sm:text-left">
                <span className="text-sm font-bold uppercase text-slate-400">
                  Live current-product units
                </span>
                <strong className="block text-3xl sm:text-4xl">
                  {presentation?.total_units_ordered ?? 0}
                </strong>
                <small className="text-slate-400">
                  {presentation?.sub_event_units_ordered ?? 0} units across{" "}
                  {presentation?.sub_event_name ?? "this event"}
                </small>
              </div>
              <div className="flex min-w-48 flex-col items-center text-center">
                {brandingUrl ? (
                  // Protected event-brand blob URL.
                  // eslint-disable-next-line @next/next/no-img-element
                  <img
                    alt={`${presentation?.event_name ?? "Event"} branding`}
                    className="mb-1 max-h-14 max-w-40 object-contain"
                    src={brandingUrl}
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
                <strong className="block text-3xl sm:text-4xl">
                  ${presentation?.total_combined_spend ?? "0.00"}
                </strong>
                <small className="text-slate-400">
                  ${presentation?.sub_event_combined_spend ?? "0.00"} across{" "}
                  {presentation?.sub_event_name ?? "this event"}
                </small>
              </div>
            </section>
          </div>
        )
      ) : (
        <div className="flex flex-1 items-center justify-center text-4xl text-slate-500">
          Waiting for the presenter to start…
        </div>
      )}
    </main>
  );
}
