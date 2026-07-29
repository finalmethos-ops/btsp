"use client";

import Link from "next/link";
import { FormEvent, useCallback, useMemo, useState, useEffect } from "react";
import { EventAccessUnavailable } from "@/components/EventAccessUnavailable";
import { useEventBrandAsset } from "@/components/EventBrandingProvider";
import {
  addEventBuyFairLine,
  createEventBuyFairOrders,
  deleteEventBuyFairOrder,
  EventBuyFairWorkspace,
  getEventBuyFairWorkspace,
  removeEventBuyFairLine,
  submitEventBuyFairOrder,
  updateEventBuyFairOrderDate,
} from "@/lib/event-buy-fair-api";
import { LifecycleLinePayload } from "@/lib/order-lifecycle-api";

const money = (value: string) =>
  new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
  }).format(Number(value));

export function EventVendorBuyFairWorkspace({
  subEventId,
}: {
  subEventId: string;
}) {
  const [workspace, setWorkspace] = useState<EventBuyFairWorkspace | null>(
    null,
  );
  const branding = useEventBrandAsset(workspace?.event_id);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [selectedStores, setSelectedStores] = useState<string[]>([]);
  const [requesterId, setRequesterId] = useState("");
  const [cart, setCart] = useState<LifecycleLinePayload[]>([]);
  const [modelCode, setModelCode] = useState("");
  const [modelSearch, setModelSearch] = useState("");
  const [quantity, setQuantity] = useState(1);
  const [deliveryDate, setDeliveryDate] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const load = useCallback(async () => {
    const next = await getEventBuyFairWorkspace(subEventId);
    setWorkspace(next);
    setError(null);
    setSelectedId((current) =>
      next.orders.some((item) => item.id === current)
        ? current
        : (next.orders[0]?.id ?? null),
    );
  }, [subEventId]);

  useEffect(() => {
    void load().catch((caught: unknown) =>
      setError(
        caught instanceof Error ? caught.message : "Buy fair could not load",
      ),
    );
  }, [load]);

  const selected =
    workspace?.orders.find((item) => item.id === selectedId) ?? null;
  const boothModels =
    workspace?.models.filter((item) => item.is_booth_model) ?? [];
  const catalogModels =
    workspace?.models.filter((item) => !item.is_booth_model) ?? [];
  const matchingModels = useCallback(
    (models: typeof boothModels) => {
      const query = modelSearch.trim().toLowerCase();
      if (!query) return models;
      return models.filter((model) =>
        [model.model_identifier, model.product_code, model.name]
          .filter(Boolean)
          .some((value) => String(value).toLowerCase().includes(query)),
      );
    },
    [modelSearch],
  );
  const matchingBoothModels = matchingModels(boothModels);
  const matchingCatalogModels = matchingModels(catalogModels);
  const selectedModel = workspace?.models.find(
    (item) => item.product_code === modelCode,
  );
  const selectedRequester = workspace?.requesters.find(
    (requester) => requester.id === Number(requesterId),
  );
  const availableStores = useMemo(() => {
    if (!selectedRequester) return workspace?.stores ?? [];
    const entity = selectedRequester.entity_code?.trim().toUpperCase() ?? "";
    const region = selectedRequester.region_code?.trim().toUpperCase() ?? "";
    if (!entity && !region) return [];
    return (workspace?.stores ?? []).filter((store) => {
      const storeEntity = store.entity_code?.trim().toUpperCase() ?? "";
      const storeRegion = store.region_code.trim().toUpperCase();
      return (
        (!entity || storeEntity === entity) &&
        (region === "ALL_STORES" || !region || storeRegion === region)
      );
    });
  }, [selectedRequester, workspace?.stores]);

  useEffect(() => {
    setSelectedStores((current) =>
      current.filter((storeNumber) =>
        availableStores.some((store) => store.store_number === storeNumber),
      ),
    );
  }, [availableStores]);
  const cartTotal = useMemo(
    () =>
      cart.reduce((total, line) => {
        const model = workspace?.models.find(
          (item) => item.product_code === line.product_code,
        );
        return total + Number(model?.unit_price ?? 0) * line.quantity;
      }, 0),
    [cart, workspace?.models],
  );

  async function run(operation: () => Promise<void>) {
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      await operation();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Operation failed");
    } finally {
      setBusy(false);
    }
  }

  function addToCart() {
    if (!modelCode) return;
    setCart((current) => {
      const existing = current.find((item) => item.product_code === modelCode);
      return existing
        ? current.map((item) =>
            item.product_code === modelCode
              ? { ...item, quantity: item.quantity + quantity }
              : item,
          )
        : [...current, { product_code: modelCode, quantity, notes: "" }];
    });
    setModelCode("");
    setQuantity(1);
  }

  async function createOrders(event: FormEvent) {
    event.preventDefault();
    await run(async () => {
      const created = await createEventBuyFairOrders(
        subEventId,
        Number(requesterId),
        selectedStores,
        deliveryDate,
        cart,
      );
      setCart([]);
      setSelectedStores([]);
      setDeliveryDate("");
      await load();
      setSelectedId(created[0]?.id ?? null);
      setNotice(
        created.length === 1
          ? "Event order draft created."
          : `${created.length} event order drafts created.`,
      );
    });
  }

  if (!workspace && error)
    return (
      <EventAccessUnavailable message={error} title="Buy fair unavailable" />
    );

  if (!workspace)
    return <main className="loading-screen">Opening vendor buy fair…</main>;

  return (
    <main className="event-ui mx-auto max-w-7xl p-4 sm:p-8">
      <Link className="text-sm text-slate-600" href="/events/entry">
        ← Event home
      </Link>
      <header
        className={branding.brandedClassName(
          "mt-4 rounded-2xl bg-slate-950 p-5 text-white",
        )}
        style={branding.brandedStyle()}
      >
        <p className="brand-eyebrow">{workspace.event_name}</p>
        <h1 className="text-3xl font-bold">{workspace.sub_event_name}</h1>
        <p>Vendor {workspace.vendor_code} · event buying workspace</p>
        <div className="mt-4 grid gap-3 sm:grid-cols-3">
          <div className="rounded-xl bg-white/10 p-3">
            <span className="block text-xs uppercase">
              {workspace.sub_event_name} orders
            </span>
            <strong className="text-xl">{workspace.order_count}</strong>
          </div>
          <div className="rounded-xl bg-white/10 p-3">
            <span className="block text-xs uppercase">Units</span>
            <strong className="text-xl">{workspace.total_units}</strong>
          </div>
          <div className="rounded-xl bg-white/10 p-3">
            <span className="block text-xs uppercase">Order volume</span>
            <strong className="text-xl">{money(workspace.total_volume)}</strong>
          </div>
        </div>
      </header>
      {error ? (
        <p className="mt-4 rounded-xl bg-red-50 p-3 text-red-800">{error}</p>
      ) : null}
      {notice ? (
        <p className="mt-4 rounded-xl bg-green-50 p-3 text-green-800">
          {notice}
        </p>
      ) : null}

      <form
        className="mt-5 rounded-2xl border bg-white p-5"
        onSubmit={createOrders}
      >
        <p className="brand-eyebrow">New event order</p>
        <h2 className="text-xl font-bold">Build the model cart</h2>
        <label className="mt-3 block font-bold">
          Requested by Buddy’s user
          <select
            className="mt-1 w-full rounded-xl border p-3"
            required
            value={requesterId}
            onChange={(event) => setRequesterId(event.target.value)}
          >
            <option value="">Select authorized requester</option>
            {workspace.requesters.map((requester) => (
              <option key={requester.id} value={requester.id}>
                {requester.display_name} —{" "}
                {requester.entity_code ?? "No entity"} /{" "}
                {requester.region_code ?? "No region"}
              </option>
            ))}
          </select>
        </label>
        <label className="mt-3 block font-bold">
          Search models
          <input
            className="mt-1 w-full rounded-xl border p-3"
            onChange={(event) => setModelSearch(event.target.value)}
            placeholder="Type a model number, code, or name"
            type="search"
            value={modelSearch}
          />
        </label>
        <div className="mt-3 grid gap-3 md:grid-cols-[1fr_120px_auto]">
          <select
            className="rounded-xl border p-3"
            onChange={(event) => setModelCode(event.target.value)}
            value={modelCode}
          >
            <option value="">Select model</option>
            {boothModels.length ? (
              <optgroup label="Models at this vendor booth">
                {matchingBoothModels.map((model) => (
                  <option key={model.product_code} value={model.product_code}>
                    ★ {model.model_identifier} — {model.name}
                  </option>
                ))}
              </optgroup>
            ) : null}
            <optgroup label="Full vendor catalog">
              {matchingCatalogModels.map((model) => (
                <option key={model.product_code} value={model.product_code}>
                  {model.model_identifier} — {model.name}
                </option>
              ))}
            </optgroup>
          </select>
          <input
            className="rounded-xl border p-3"
            min={Number(selectedModel?.minimum_order_quantity ?? 1)}
            onChange={(event) =>
              setQuantity(Math.max(1, Number(event.target.value)))
            }
            type="number"
            value={quantity}
          />
          <button
            className="rounded-xl bg-blue-900 px-5 py-3 font-bold text-white"
            disabled={!modelCode}
            onClick={addToCart}
            type="button"
          >
            Add model
          </button>
        </div>
        <div className="event-buy-fair-cart mt-3 space-y-2">
          {cart.map((line) => {
            const model = workspace.models.find(
              (item) => item.product_code === line.product_code,
            );
            return (
              <div
                className="event-buy-fair-line event-buy-fair-cart-line grid grid-cols-[minmax(0,1fr)_5rem_auto] items-center gap-3 rounded-xl bg-slate-50 p-3"
                key={line.product_code}
              >
                <span className="min-w-0">
                  <strong>{model?.model_identifier}</strong>
                  <small className="ml-2 text-slate-500">{model?.name}</small>
                </span>
                <input
                  aria-label={`Quantity for ${model?.model_identifier}`}
                  className="w-full rounded-lg border p-2"
                  min="1"
                  onChange={(event) =>
                    setCart((current) =>
                      current.map((item) =>
                        item.product_code === line.product_code
                          ? {
                              ...item,
                              quantity: Math.max(1, Number(event.target.value)),
                            }
                          : item,
                      ),
                    )
                  }
                  type="number"
                  value={line.quantity}
                />
                <button
                  className="rounded-lg border px-3 py-2"
                  onClick={() =>
                    setCart((current) =>
                      current.filter(
                        (item) => item.product_code !== line.product_code,
                      ),
                    )
                  }
                  type="button"
                >
                  Remove
                </button>
              </div>
            );
          })}
        </div>
        <h2 className="mt-5 font-bold">Choose stores</h2>
        <div className="event-buy-fair-store-list mt-2 grid max-h-56 gap-2 overflow-auto rounded-xl border p-3 sm:grid-cols-2 lg:grid-cols-3">
          {availableStores.map((store) => (
            <label
              className={`event-selectable flex gap-2 rounded-lg border p-3 ${selectedStores.includes(store.store_number) ? "is-selected" : ""}`}
              key={store.store_number}
            >
              <input
                checked={selectedStores.includes(store.store_number)}
                onChange={(event) =>
                  setSelectedStores((current) =>
                    event.target.checked
                      ? [...current, store.store_number]
                      : current.filter((item) => item !== store.store_number),
                  )
                }
                type="checkbox"
              />
              <span>
                <strong>{store.store_number}</strong> — {store.name}
                <small className="block text-slate-500">
                  {store.city}, {store.state_code}
                </small>
              </span>
            </label>
          ))}
          {requesterId && !availableStores.length ? (
            <p className="rounded-lg border border-dashed p-3 text-sm text-slate-500">
              No active stores are assigned to this requester&apos;s entity and
              region.
            </p>
          ) : null}
        </div>
        <div className="event-buy-fair-submit-row mt-3 flex flex-wrap items-end gap-3">
          <label className="font-bold">
            Requested Delivery Date
            <input
              className="mt-1 block rounded-xl border p-3"
              onChange={(event) => setDeliveryDate(event.target.value)}
              required
              type="date"
              value={deliveryDate}
            />
          </label>
          <span className="font-bold">
            Cart total per store: {money(String(cartTotal))}
          </span>
          <button
            className="rounded-xl bg-blue-900 px-5 py-3 font-bold text-white disabled:bg-slate-400"
            disabled={
              busy || !cart.length || !selectedStores.length || !requesterId
            }
          >
            Create {selectedStores.length || ""} order draft
            {selectedStores.length === 1 ? "" : "s"}
          </button>
        </div>
      </form>

      <div className="mt-5 grid gap-5 lg:grid-cols-[340px_1fr]">
        <section className="rounded-2xl border bg-white p-3">
          <h2 className="p-2 font-bold">
            {workspace.sub_event_name} order drafts and submissions
          </h2>
          {workspace.orders.map((order) => (
            <button
              className={`mb-2 w-full rounded-xl border p-3 text-left ${selectedId === order.id ? "selected-object" : ""}`}
              key={order.id}
              onClick={() => setSelectedId(order.id)}
              type="button"
            >
              <strong className="break-words">{order.order_number}</strong>
              <span className="block text-xs text-slate-500">
                Store {order.store_number} · {order.status.replaceAll("_", " ")}
              </span>
              <span className="font-semibold">{money(order.total)}</span>
            </button>
          ))}
        </section>
        {selected ? (
          <section className="space-y-3 rounded-2xl border bg-white p-5">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <h2 className="break-words text-xl font-bold">
                  {selected.order_number}
                </h2>
                <p>
                  Store {selected.store_number} · {money(selected.total)}
                </p>
              </div>
              <div className="text-right">
                <span className="block text-xs font-bold uppercase tracking-wide text-slate-500">
                  Requested delivery date
                </span>
                <strong className="block text-lg">
                  {selected.expected_delivery_date ?? "Not set"}
                </strong>
              </div>
            </div>
            {selected.line_items.map((line) => (
              <div
                className="event-buy-fair-line event-buy-fair-draft-line flex flex-wrap items-center gap-3 rounded-xl bg-slate-50 p-3"
                key={line.id}
              >
                <span className="flex-1">
                  <strong>{line.product_code}</strong>
                  <small className="block text-slate-500">
                    {line.product_name}
                  </small>
                </span>
                <span>Qty {line.quantity}</span>
                {selected.status === "vendor_draft" ? (
                  <button
                    className="rounded-lg border px-3 py-2"
                    disabled={busy}
                    onClick={() =>
                      void run(async () => {
                        await removeEventBuyFairLine(
                          subEventId,
                          selected.id,
                          line.id,
                        );
                        await load();
                      })
                    }
                    type="button"
                  >
                    Remove
                  </button>
                ) : null}
              </div>
            ))}
            {selected.status === "vendor_draft" ? (
              <form
                className="grid gap-2 sm:grid-cols-[1fr_100px_auto]"
                onSubmit={(event: FormEvent<HTMLFormElement>) => {
                  event.preventDefault();
                  const formElement = event.currentTarget;
                  const data = new FormData(formElement);
                  void run(async () => {
                    await addEventBuyFairLine(subEventId, selected.id, {
                      product_code: String(data.get("product_code")),
                      quantity: Number(data.get("quantity")),
                    });
                    await load();
                    formElement.reset();
                  });
                }}
              >
                <select
                  className="rounded-xl border p-3"
                  name="product_code"
                  required
                >
                  <option value="">Add another model</option>
                  {workspace.models.map((model) => (
                    <option key={model.product_code} value={model.product_code}>
                      {model.is_booth_model ? "★ " : ""}
                      {model.model_identifier} — {model.name}
                    </option>
                  ))}
                </select>
                <input
                  className="rounded-xl border p-3"
                  min="1"
                  name="quantity"
                  required
                  type="number"
                />
                <button className="rounded-xl border px-4 font-bold">
                  Add
                </button>
              </form>
            ) : null}
            {selected.status === "vendor_draft" ? (
              <div className="flex flex-wrap gap-2">
                <button
                  className="rounded-xl bg-green-700 px-5 py-3 font-bold text-white"
                  disabled={busy}
                  onClick={() =>
                    void run(async () => {
                      await submitEventBuyFairOrder(subEventId, selected.id);
                      await load();
                      setNotice(
                        "Event order submitted into the standard Purchasing workflow.",
                      );
                    })
                  }
                  type="button"
                >
                  Submit to Purchasing
                </button>
                <button
                  className="rounded-xl border px-4 py-3 font-bold"
                  disabled={busy}
                  onClick={() => {
                    const nextDate = window.prompt(
                      "Expected delivery date (YYYY-MM-DD)",
                      selected.expected_delivery_date ?? "",
                    );
                    if (nextDate)
                      void run(async () => {
                        await updateEventBuyFairOrderDate(
                          subEventId,
                          selected.id,
                          nextDate,
                        );
                        await load();
                      });
                  }}
                  type="button"
                >
                  Change delivery date
                </button>
                <button
                  className="rounded-xl bg-red-700 px-4 py-3 font-bold text-white"
                  disabled={busy}
                  onClick={() => {
                    if (window.confirm("Delete this event order draft?"))
                      void run(async () => {
                        await deleteEventBuyFairOrder(subEventId, selected.id);
                        await load();
                      });
                  }}
                  type="button"
                >
                  Delete draft
                </button>
              </div>
            ) : (
              <p className="rounded-xl bg-green-50 p-3 text-green-800">
                Submitted to the standard Purchasing review queue.
              </p>
            )}
          </section>
        ) : null}
      </div>
    </main>
  );
}
