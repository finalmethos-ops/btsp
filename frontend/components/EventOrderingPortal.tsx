"use client";

import { FormEvent, useEffect, useRef, useState } from "react";
import {
  EventOrderingWorkspace,
  getEventOrderingWorkspace,
  submitEventOrder,
} from "@/lib/event-ordering-api";
import { useEventBrandAsset } from "@/components/EventBrandingProvider";
import { downloadPresentationImage } from "@/lib/event-presentation-api";
import { subscribeEventRealtime } from "@/lib/event-realtime";
import { EventAccessUnavailable } from "@/components/EventAccessUnavailable";
import { EventLivePoll } from "@/components/EventLivePoll";
import {
  buildEventOrderPayload,
  eventOrderEstimatedSpend,
  initialEventOrderQuantities,
} from "@/lib/event-order-quantities";

export function EventOrderingPortal({ subEventId }: { subEventId: string }) {
  const [workspace, setWorkspace] = useState<EventOrderingWorkspace | null>(
    null,
  );
  const eventBranding = useEventBrandAsset(workspace?.event_id);
  const [imageUrl, setImageUrl] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [orderError, setOrderError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [draftQuantities, setDraftQuantities] = useState<
    Record<string, number>
  >({});
  const draftSourceKey = `${workspace?.current_slide?.id ?? "none"}:${workspace?.existing_order?.updated_at ?? "new"}`;
  const hydratedDraftSource = useRef("");

  useEffect(() => {
    let active = true;
    const refresh = () =>
      void getEventOrderingWorkspace(subEventId)
        .then((value) => {
          if (active) {
            setWorkspace(value);
            setError(null);
          }
        })
        .catch((caught: unknown) => {
          if (active)
            setError(
              caught instanceof Error
                ? caught.message
                : "Unable to load the event.",
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

  const slide = workspace?.current_slide;
  useEffect(() => {
    if (hydratedDraftSource.current === draftSourceKey) return;
    hydratedDraftSource.current = draftSourceKey;
    if (!slide) {
      setDraftQuantities({});
      return;
    }
    setDraftQuantities(
      initialEventOrderQuantities(slide, workspace?.existing_order ?? null),
    );
  }, [draftSourceKey, slide, workspace?.existing_order]);
  const estimatedSpend = slide
    ? eventOrderEstimatedSpend(slide, draftQuantities)
    : 0;

  function setDraftQuantity(key: string, rawValue: string) {
    setMessage(null);
    setOrderError(null);
    setDraftQuantities((current) => {
      const updated = { ...current };
      if (rawValue === "") delete updated[key];
      else updated[key] = Number(rawValue);
      return updated;
    });
  }

  useEffect(() => {
    let url: string | null = null;
    setImageUrl(null);
    if (slide?.has_image)
      void downloadPresentationImage(slide.id).then((blob) => {
        url = URL.createObjectURL(blob);
        setImageUrl(url);
      });
    return () => {
      if (url) URL.revokeObjectURL(url);
    };
  }, [slide?.has_image, slide?.id]);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setOrderError(null);
    setMessage(null);
    try {
      if (!slide) throw new Error("No current product is available.");
      const updated = await submitEventOrder(
        subEventId,
        buildEventOrderPayload(slide, draftQuantities),
      );
      setWorkspace(updated);
      setMessage(
        updated.existing_order?.status === "waitlisted"
          ? "Quantity recorded on the waitlist."
          : "Order confirmed for your entity.",
      );
    } catch (caught) {
      setOrderError(
        caught instanceof Error
          ? caught.message
          : "Unable to submit the order.",
      );
    } finally {
      setBusy(false);
    }
  }

  if (!workspace && error)
    return (
      <EventAccessUnavailable message={error} title="Ordering unavailable" />
    );

  if (!workspace)
    return <main className="loading-screen">Connecting to live event…</main>;
  return (
    <main className="event-ui mx-auto max-w-5xl p-4 sm:p-8">
      <header
        className={eventBranding.brandedClassName(
          "mb-5 rounded-2xl bg-slate-950 p-5 text-white",
        )}
        style={eventBranding.brandedStyle()}
      >
        <p className="text-blue-300">{workspace.event_name}</p>
        <h1 className="text-2xl font-bold">{workspace.sub_event_name}</h1>
        <p>
          Ordering entity: <strong>{workspace.entity_code}</strong>
        </p>
      </header>
      <EventLivePoll subEventId={subEventId} />
      {workspace.ordering_status === "open" ? (
        <div className="event-order-live-banner mb-5 flex items-center justify-between rounded-xl border border-green-500 bg-green-950 p-4 text-white">
          <strong className="text-green-400">ORDERS ARE LIVE</strong>
          <span>Open until the presenter moves forward</span>
        </div>
      ) : null}
      <section className="mb-5">
        <div className="rounded-2xl border bg-slate-950 p-4 text-white">
          <span className="text-xs font-bold uppercase text-blue-300">
            Your {workspace.sub_event_name} commitment
          </span>
          <strong className="mt-1 block text-3xl">
            ${workspace.entity_sub_event_spend}
          </strong>
        </div>
      </section>
      {error ? (
        <p className="mb-4 rounded-xl bg-red-50 p-3 text-red-800">{error}</p>
      ) : null}
      {!slide ? (
        <section className="rounded-2xl border p-5 text-center text-lg text-slate-500 sm:p-10 sm:text-xl">
          Waiting for the presenter to begin…
        </section>
      ) : slide.slide_type === "filler" ? (
        <section
          className={eventBranding.brandedClassName(
            "rounded-2xl border bg-white p-6 text-center sm:p-10",
          )}
          style={eventBranding.brandedStyle()}
        >
          <p className="brand-eyebrow">
            {slide.filler_category?.replaceAll("_", " ")}
          </p>
          {imageUrl ? (
            // Authenticated blob URL.
            // eslint-disable-next-line @next/next/no-img-element
            <img
              alt={slide.name}
              className="mx-auto mb-6 max-h-96 w-full rounded-xl object-contain"
              src={imageUrl}
            />
          ) : null}
          <h2 className="text-3xl font-black sm:text-5xl">{slide.name}</h2>
          {slide.description ? (
            <p className="mx-auto mt-5 max-w-3xl whitespace-pre-line text-lg">
              {slide.description}
            </p>
          ) : null}
          <p className="mt-6 font-semibold text-slate-500">
            No order is requested for this slide.
          </p>
        </section>
      ) : (
        <section
          className={eventBranding.brandedClassName(
            "grid gap-6 rounded-2xl border bg-white p-5 lg:grid-cols-2",
          )}
          style={eventBranding.brandedStyle()}
        >
          <div>
            {imageUrl ? (
              // Authenticated blob URL.
              // eslint-disable-next-line @next/next/no-img-element
              <img
                alt={slide.name}
                className="max-h-96 w-full rounded-xl object-contain"
                src={imageUrl}
              />
            ) : (
              <div className="flex min-h-72 items-center justify-center rounded-xl bg-slate-100 text-slate-400">
                Product image
              </div>
            )}
          </div>
          <div>
            <p className="brand-eyebrow">Current product</p>
            <h2 className="text-2xl font-bold sm:text-3xl">{slide.name}</h2>
            <p className="text-xl text-slate-600">{slide.model_number}</p>
            <p className="mt-4">{slide.description}</p>
            {!slide.product_variants.length ? (
              <dl className="mt-5 grid gap-3 text-sm sm:grid-cols-2">
                <div>
                  <dt>Event cost</dt>
                  <dd className="text-xl font-bold">
                    ${slide.event_unit_cost}
                  </dd>
                </div>
                <div>
                  <dt>Standard Cost</dt>
                  <dd className="text-xl font-bold">
                    ${slide.standard_cost ?? "—"}
                  </dd>
                  {slide.standard_cost &&
                  Number(slide.standard_cost) >
                    Number(slide.event_unit_cost) ? (
                    <dd className="mt-1 font-black text-amber-700">
                      You save ${" "}
                      {(
                        Number(slide.standard_cost) -
                        Number(slide.event_unit_cost)
                      ).toFixed(2)}{" "}
                      per unit
                    </dd>
                  ) : null}
                </div>
                <div>
                  <dt>MOQ</dt>
                  <dd className="font-bold">{slide.minimum_order_quantity}</dd>
                </div>
                <div>
                  <dt>Remaining</dt>
                  <dd className="font-bold">
                    {workspace.units_remaining ?? "Not limited"}
                  </dd>
                </div>
              </dl>
            ) : null}
            <form
              className="mt-6 grid gap-3"
              key={`${slide.id}-${workspace.existing_order?.updated_at ?? "new"}`}
              onSubmit={submit}
            >
              {slide.product_variants.length ? (
                <fieldset className="grid gap-3 rounded-xl border p-3">
                  <legend className="px-2 font-bold">
                    Choose product quantities
                  </legend>
                  {slide.product_variants.map((variant) => (
                    <label
                      className="event-order-variant-row grid min-w-0 grid-cols-1 items-center gap-3 sm:grid-cols-[minmax(0,1fr)_100px]"
                      key={variant.model_number}
                    >
                      <span className="min-w-0 break-words">
                        <strong>{variant.name}</strong>
                        <small className="block text-slate-500">
                          {variant.model_number} · ${variant.event_unit_cost} ·
                          MOQ {variant.minimum_order_quantity} · Remaining{" "}
                          {workspace.variant_units_remaining[
                            variant.model_number
                          ] ?? "Not limited"}
                        </small>
                        {variant.standard_cost &&
                        Number(variant.standard_cost) >
                          Number(variant.event_unit_cost) ? (
                          <small className="mt-1 block font-bold text-amber-700">
                            Save ${" "}
                            {(
                              Number(variant.standard_cost) -
                              Number(variant.event_unit_cost)
                            ).toFixed(2)}{" "}
                            each
                          </small>
                        ) : null}
                      </span>
                      <input
                        aria-label={`${variant.name} quantity`}
                        className="w-full rounded-lg border p-3"
                        inputMode="numeric"
                        min="0"
                        name={`variant__${variant.model_number}`}
                        onChange={(input) =>
                          setDraftQuantity(
                            variant.model_number,
                            input.target.value,
                          )
                        }
                        placeholder="Qty"
                        step="1"
                        type="number"
                        value={draftQuantities[variant.model_number] ?? ""}
                      />
                      <small className="event-order-variant-total text-left font-bold text-slate-700 sm:col-span-2 sm:text-right">
                        Line total: ${" "}
                        {(
                          (draftQuantities[variant.model_number] ?? 0) *
                          Number(variant.event_unit_cost)
                        ).toLocaleString(undefined, {
                          minimumFractionDigits: 2,
                          maximumFractionDigits: 2,
                        })}
                      </small>
                    </label>
                  ))}
                </fieldset>
              ) : (
                <label className="font-semibold">
                  Quantity
                  <input
                    className="mt-1 w-full rounded-lg border p-3"
                    inputMode="numeric"
                    min={slide.minimum_order_quantity}
                    name="quantity"
                    onChange={(input) =>
                      setDraftQuantity("__primary", input.target.value)
                    }
                    placeholder="Enter quantity"
                    required
                    step="1"
                    type="number"
                    value={draftQuantities.__primary ?? ""}
                  />
                </label>
              )}
              <div className="event-order-estimated-spend flex items-center justify-between rounded-xl bg-slate-950 p-4 text-white">
                <span className="text-sm font-bold uppercase text-blue-300">
                  Estimated spend
                </span>
                <strong className="text-2xl">
                  $
                  {estimatedSpend.toLocaleString(undefined, {
                    minimumFractionDigits: 2,
                    maximumFractionDigits: 2,
                  })}
                </strong>
              </div>
              {orderError ? (
                <p
                  className="event-order-submit-error rounded-xl border border-red-300 bg-red-50 p-3 text-red-900"
                  id="event-order-submit-error"
                  role="alert"
                >
                  {orderError}
                </p>
              ) : null}
              <button
                aria-describedby={
                  orderError
                    ? "event-order-submit-error"
                    : message
                      ? "event-order-submit-confirmation"
                      : undefined
                }
                className="rounded-xl bg-blue-800 p-3 font-bold text-white disabled:bg-slate-400"
                disabled={busy || workspace.ordering_status !== "open"}
              >
                {workspace.ordering_status === "open"
                  ? busy
                    ? "Submitting…"
                    : workspace.existing_order
                      ? "Update entity order"
                      : "Submit entity order"
                  : "Ordering is closed"}
              </button>
              {message ? (
                <p
                  aria-live="polite"
                  className="event-order-submit-confirmation rounded-xl border border-green-300 bg-green-50 p-3 text-center font-bold text-green-900"
                  id="event-order-submit-confirmation"
                  role="status"
                >
                  ✓ {message}
                </p>
              ) : null}
            </form>
          </div>
        </section>
      )}
    </main>
  );
}
