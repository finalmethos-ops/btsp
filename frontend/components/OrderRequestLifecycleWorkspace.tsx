"use client";

import Link from "next/link";
import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import { useAuth } from "@/lib/auth";
import {
  addPurchasingRequestLine,
  addVendorRequestLine,
  createVendorOrderRequests,
  decidePurchasingRequest,
  deletePurchasingRequestLine,
  deleteVendorOrderRequest,
  deleteVendorRequestLine,
  LifecycleLinePayload,
  listPurchasingOrderRequests,
  listVendorOrderRequests,
  submitVendorOrderRequest,
  updatePurchasingRequestLine,
  updateVendorRequestLine,
  updateVendorOrderRequestDate,
} from "@/lib/order-lifecycle-api";
import { searchModelCatalog } from "@/lib/model-catalog-api";
import {
  EligibleStore,
  listEligibleStores,
  PurchaseRequest,
} from "@/lib/purchasing-api";
import { listVendorModels, VendorModel } from "@/lib/vendor-model-api";

const money = (value: string) =>
  new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" }).format(
    Number(value),
  );

export function OrderRequestLifecycleWorkspace({
  mode,
}: {
  mode: "vendor" | "purchasing";
}) {
  const { user } = useAuth();
  const [requests, setRequests] = useState<PurchaseRequest[]>([]);
  const [selected, setSelected] = useState<PurchaseRequest | null>(null);
  const [models, setModels] = useState<VendorModel[]>([]);
  const [stores, setStores] = useState<EligibleStore[]>([]);
  const [storeNumber, setStoreNumber] = useState("");
  const [orderMode, setOrderMode] = useState<"single" | "multiple">("single");
  const [entityCode, setEntityCode] = useState("");
  const [regionCode, setRegionCode] = useState("");
  const [selectedStores, setSelectedStores] = useState<string[]>([]);
  const [cart, setCart] = useState<LifecycleLinePayload[]>([]);
  const [cartProductCode, setCartProductCode] = useState("");
  const [cartQuantity, setCartQuantity] = useState(1);
  const [newExpectedDate, setNewExpectedDate] = useState("");
  const [approvalExpectedDate, setApprovalExpectedDate] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const load = useCallback(async () => {
    const next =
      mode === "vendor"
        ? await listVendorOrderRequests()
        : await listPurchasingOrderRequests();
    setRequests(next);
    setSelected(
      (current) =>
        next.find((item) => item.id === current?.id) ?? next[0] ?? null,
    );
  }, [mode]);
  useEffect(() => {
    void load().catch((caught: unknown) =>
      setError(
        caught instanceof Error ? caught.message : "Unable to load requests.",
      ),
    );
  }, [load]);
  useEffect(() => {
    if (mode === "vendor" && user?.vendor_code) {
      void Promise.all([
        listVendorModels(),
        listEligibleStores(user.vendor_code),
      ]).then(([nextModels, nextStores]) => {
        setModels(nextModels);
        setStores(nextStores);
      });
    }
  }, [mode, user?.vendor_code]);
  useEffect(() => {
    if (mode === "purchasing" && selected)
      void searchModelCatalog("", selected.vendor_code).then(setModels);
  }, [mode, selected]);
  useEffect(() => {
    setApprovalExpectedDate(selected?.expected_delivery_date ?? "");
  }, [selected]);
  const entities = useMemo(
    () =>
      Array.from(
        new Set(stores.map((store) => store.entity_code).filter(Boolean)),
      ).sort() as string[],
    [stores],
  );
  const regions = useMemo(
    () =>
      Array.from(
        new Set(
          stores
            .filter((store) => store.entity_code === entityCode)
            .map((store) => store.region_code),
        ),
      ).sort(),
    [entityCode, stores],
  );
  const regionalStores = useMemo(
    () =>
      stores.filter(
        (store) =>
          store.entity_code === entityCode && store.region_code === regionCode,
      ),
    [entityCode, regionCode, stores],
  );
  async function run(operation: () => Promise<void>) {
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      await operation();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Operation failed.");
    } finally {
      setBusy(false);
    }
  }
  async function create(event: FormEvent) {
    event.preventDefault();
    await run(async () => {
      const storeNumbers =
        orderMode === "single" ? [storeNumber] : selectedStores;
      const created = await createVendorOrderRequests(
        storeNumbers,
        newExpectedDate,
        cart,
      );
      await load();
      setSelected(created[0]);
      setStoreNumber("");
      setSelectedStores([]);
      setNewExpectedDate("");
      setCart([]);
      setNotice(
        created.length === 1
          ? "Draft order created."
          : `${created.length} separate draft orders created.`,
      );
    });
  }
  async function addLine(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selected) return;
    const form = event.currentTarget;
    const data = new FormData(form);
    const payload: LifecycleLinePayload = {
      product_code: String(data.get("product_code")),
      quantity: Number(data.get("quantity")),
      notes: String(data.get("notes") || ""),
    };
    await run(async () => {
      const item =
        mode === "vendor"
          ? await addVendorRequestLine(selected.id, payload)
          : await addPurchasingRequestLine(selected.id, payload);
      setSelected(item);
      await load();
      form.reset();
    });
  }
  async function updateLine(lineId: number, event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selected) return;
    const data = new FormData(event.currentTarget);
    const payload: LifecycleLinePayload = {
      product_code: String(data.get("product_code")),
      quantity: Number(data.get("quantity")),
      notes: String(data.get("notes") || ""),
    };
    await run(async () => {
      const item =
        mode === "vendor"
          ? await updateVendorRequestLine(selected.id, lineId, payload)
          : await updatePurchasingRequestLine(selected.id, lineId, payload);
      setSelected(item);
      await load();
    });
  }
  const editable =
    selected && (mode === "purchasing" || selected.status === "vendor_draft");

  return (
    <main className="mx-auto max-w-7xl p-4 sm:p-8">
      <Link className="text-sm text-slate-600" href="/">
        ← Command center
      </Link>
      <p className="brand-eyebrow mt-4">
        {mode === "vendor" ? "Vendor ordering" : "Purchasing review"}
      </p>
      <h1 className="mt-2 text-3xl font-bold">
        {mode === "vendor" ? "Order Requests" : "Order Review"}
      </h1>
      <p className="mt-2 text-slate-600">
        {mode === "vendor"
          ? "Build an order request and submit it to Purchasing for review."
          : "Edit submitted requests, then approve them into POs or cancel them."}
      </p>
      {error && !selected ? (
        <p className="mt-4 rounded-xl bg-red-50 p-3 text-red-800">{error}</p>
      ) : null}
      {notice ? (
        <p className="mt-4 rounded-xl bg-green-50 p-3 text-green-800">
          {notice}
        </p>
      ) : null}
      {mode === "vendor" ? (
        <form className="mt-5 rounded-2xl bg-white p-4" onSubmit={create}>
          <div className="rounded-xl border border-yellow-500 bg-yellow-300 p-4 text-slate-950 shadow-sm">
            <h2 className="font-bold text-slate-950">
              1. Build the order cart
            </h2>
            <p className="mt-1 text-sm font-medium text-slate-800">
              This cart will be copied into a separate draft for every selected
              store.
            </p>
            <div className="mt-3 grid gap-3 md:grid-cols-[2fr_120px_auto]">
              <select
                className="rounded-xl border border-yellow-600 bg-white p-3 text-slate-950"
                onChange={(event) => setCartProductCode(event.target.value)}
                value={cartProductCode}
              >
                <option value="">Select model</option>
                {models.map((model) => (
                  <option key={model.product_code} value={model.product_code}>
                    {model.model_identifier} — {model.name}
                  </option>
                ))}
              </select>
              <input
                className="rounded-xl border border-yellow-600 bg-white p-3 text-slate-950"
                min="1"
                onChange={(event) =>
                  setCartQuantity(Math.max(1, Number(event.target.value)))
                }
                step="1"
                type="number"
                value={cartQuantity}
              />
              <button
                className="rounded-xl bg-blue-900 px-5 py-3 font-bold text-white"
                disabled={!cartProductCode}
                onClick={() => {
                  setCart((current) => {
                    const existing = current.find(
                      (line) => line.product_code === cartProductCode,
                    );
                    return existing
                      ? current.map((line) =>
                          line.product_code === cartProductCode
                            ? {
                                ...line,
                                quantity: line.quantity + cartQuantity,
                              }
                            : line,
                        )
                      : [
                          ...current,
                          {
                            product_code: cartProductCode,
                            quantity: cartQuantity,
                            notes: "",
                          },
                        ];
                  });
                  setCartProductCode("");
                  setCartQuantity(1);
                }}
                type="button"
              >
                Add to cart
              </button>
            </div>
            <div className="mt-3 space-y-2">
              {cart.map((line) => {
                const model = models.find(
                  (item) => item.product_code === line.product_code,
                );
                return (
                  <div
                    className="flex items-center gap-3 rounded-lg bg-white p-3"
                    key={line.product_code}
                  >
                    <span className="min-w-0 flex-1">
                      <strong>
                        {model?.model_identifier ?? line.product_code}
                      </strong>
                      <small className="ml-2 font-medium text-slate-700">
                        {model?.name}
                      </small>
                    </span>
                    <input
                      aria-label={`Quantity for ${line.product_code}`}
                      className="w-24 rounded-lg border p-2"
                      min="1"
                      onChange={(event) =>
                        setCart((current) =>
                          current.map((item) =>
                            item.product_code === line.product_code
                              ? {
                                  ...item,
                                  quantity: Math.max(
                                    1,
                                    Number(event.target.value),
                                  ),
                                }
                              : item,
                          ),
                        )
                      }
                      step="1"
                      type="number"
                      value={line.quantity}
                    />
                    <button
                      className="rounded-lg bg-yellow-400 px-3 py-2 font-semibold"
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
              {!cart.length ? (
                <p className="rounded-lg bg-white p-3 text-sm font-medium text-slate-700">
                  Add at least one model before creating orders.
                </p>
              ) : null}
            </div>
          </div>
          <h2 className="mt-5 font-bold">2. Choose stores and create drafts</h2>
          <div className="flex gap-2">
            {(["single", "multiple"] as const).map((option) => (
              <button
                className={`rounded-xl px-4 py-2 font-bold ${orderMode === option ? "bg-yellow-400 text-slate-950" : "bg-slate-100"}`}
                key={option}
                onClick={() => {
                  setOrderMode(option);
                  setStoreNumber("");
                  setEntityCode("");
                  setRegionCode("");
                  setSelectedStores([]);
                }}
                type="button"
              >
                {option === "single" ? "Single store" : "Multiple stores"}
              </button>
            ))}
          </div>
          <div className="mt-4 flex flex-wrap gap-3">
            {orderMode === "single" ? (
              <select
                className="min-w-72 flex-1 rounded-xl border p-3"
                onChange={(e) => setStoreNumber(e.target.value)}
                required
                value={storeNumber}
              >
                <option value="">Select eligible store</option>
                {stores.map((store) => (
                  <option key={store.store_number} value={store.store_number}>
                    {store.store_number} — {store.name} ({store.state_code})
                  </option>
                ))}
              </select>
            ) : (
              <>
                <select
                  className="min-w-56 rounded-xl border p-3"
                  onChange={(event) => {
                    setEntityCode(event.target.value);
                    setRegionCode("");
                    setSelectedStores([]);
                  }}
                  required
                  value={entityCode}
                >
                  <option value="">Select entity</option>
                  {entities.map((entity) => (
                    <option key={entity} value={entity}>
                      {entity}
                    </option>
                  ))}
                </select>
                <select
                  className="min-w-56 rounded-xl border p-3"
                  disabled={!entityCode}
                  onChange={(event) => {
                    setRegionCode(event.target.value);
                    setSelectedStores([]);
                  }}
                  required
                  value={regionCode}
                >
                  <option value="">Select region</option>
                  {regions.map((region) => (
                    <option key={region} value={region}>
                      {region}
                    </option>
                  ))}
                </select>
              </>
            )}
            <input
              className="rounded-xl border p-3"
              onChange={(event) => setNewExpectedDate(event.target.value)}
              onClick={(event) => event.currentTarget.showPicker()}
              required
              type="date"
              value={newExpectedDate}
            />
          </div>
          {orderMode === "multiple" && regionCode ? (
            <div className="mt-4 rounded-xl border p-4">
              <label className="flex items-center gap-2 border-b pb-3 font-bold">
                <input
                  checked={
                    regionalStores.length > 0 &&
                    selectedStores.length === regionalStores.length
                  }
                  onChange={(event) =>
                    setSelectedStores(
                      event.target.checked
                        ? regionalStores.map((store) => store.store_number)
                        : [],
                    )
                  }
                  type="checkbox"
                />
                Select all {regionalStores.length} eligible stores
              </label>
              <div className="mt-3 grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
                {regionalStores.map((store) => (
                  <label
                    className={`selection-pane flex items-start gap-2 rounded-lg p-3 ${selectedStores.includes(store.store_number) ? "is-selected" : ""}`}
                    key={store.store_number}
                  >
                    <input
                      checked={selectedStores.includes(store.store_number)}
                      onChange={(event) =>
                        setSelectedStores((current) =>
                          event.target.checked
                            ? [...current, store.store_number]
                            : current.filter(
                                (number) => number !== store.store_number,
                              ),
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
              </div>
            </div>
          ) : null}
          <button
            className="mt-4 rounded-xl bg-blue-900 px-5 py-3 font-bold text-white"
            disabled={
              busy ||
              !cart.length ||
              (orderMode === "single" ? !storeNumber : !selectedStores.length)
            }
          >
            {orderMode === "single"
              ? "Create order draft"
              : `Create the same order for ${selectedStores.length} stores`}
          </button>
        </form>
      ) : null}
      <div className="mt-5 grid gap-5 lg:grid-cols-[300px_1fr]">
        <section className="rounded-2xl bg-white p-3">
          <h2 className="p-2 font-bold">Requests</h2>
          {requests.map((request) => (
            <button
              className={`mb-2 w-full rounded-xl border p-3 text-left ${selected?.id === request.id ? "selected-object" : ""}`}
              key={request.id}
              onClick={() => setSelected(request)}
            >
              <strong>{request.order_number}</strong>
              <span className="block text-xs text-slate-500">
                {request.vendor_code} · {request.status.replaceAll("_", " ")}
              </span>
              {request.context.source === "event_vendor_buy_fair" ? (
                <span className="mt-1 inline-flex rounded-full bg-blue-100 px-2 py-1 text-xs font-bold text-blue-900">
                  {String(request.context.event_name || "Event buy fair")}
                </span>
              ) : null}
              {request.context.source === "event_live_order_release" ? (
                <span className="mt-1 inline-flex rounded-full bg-green-100 px-2 py-1 text-xs font-bold text-green-900">
                  {String(request.context.event_name || "Live event release")}
                </span>
              ) : null}
              <span className="text-sm font-semibold">
                {money(request.total)}
              </span>
            </button>
          ))}
          {!requests.length ? (
            <p className="p-4 text-sm text-slate-500">
              No requests in this queue.
            </p>
          ) : null}
        </section>
        {selected ? (
          <section className="space-y-4">
            {error ? (
              <p className="rounded-xl border border-yellow-500 bg-yellow-300 p-4 font-semibold text-slate-950">
                {error}
              </p>
            ) : null}
            <div className="rounded-2xl bg-white p-5">
              <div className="flex justify-between">
                <div>
                  <h2 className="text-xl font-bold">{selected.order_number}</h2>
                  <p className="text-sm text-slate-500">
                    {selected.vendor_code}
                  </p>
                  {selected.context.source === "event_vendor_buy_fair" ? (
                    <p className="mt-2 rounded-lg bg-blue-50 p-2 text-sm font-semibold text-blue-900">
                      Event order ·{" "}
                      {String(selected.context.event_name || "Vendor buy fair")}
                      {selected.context.sub_event_name
                        ? ` · ${String(selected.context.sub_event_name)}`
                        : ""}
                    </p>
                  ) : null}
                  {selected.context.source === "event_live_order_release" ? (
                    <p className="mt-2 rounded-lg bg-green-50 p-2 text-sm font-semibold text-green-900">
                      Live event release ·{" "}
                      {String(selected.context.event_name || "Event")}
                      {selected.context.entity_code
                        ? ` · Entity ${String(selected.context.entity_code)}`
                        : ""}
                      {selected.context.release_batch_id
                        ? ` · Batch ${String(selected.context.release_batch_id)}`
                        : ""}
                    </p>
                  ) : null}
                  <label className="mt-3 block text-sm font-semibold">
                    Expected delivery date
                    <input
                      className="ml-3 rounded-lg border p-2"
                      disabled={
                        mode === "vendor" && selected.status !== "vendor_draft"
                      }
                      onChange={(event) =>
                        setApprovalExpectedDate(event.target.value)
                      }
                      onClick={(event) => event.currentTarget.showPicker()}
                      type="date"
                      value={approvalExpectedDate}
                    />
                    {mode === "vendor" && selected.status === "vendor_draft" ? (
                      <button
                        className="ml-2 rounded-lg border px-3 py-2 font-semibold"
                        disabled={!approvalExpectedDate || busy}
                        onClick={() =>
                          void run(async () => {
                            const item = await updateVendorOrderRequestDate(
                              selected.id,
                              approvalExpectedDate,
                            );
                            setSelected(item);
                            await load();
                            setNotice("Draft delivery date updated.");
                          })
                        }
                        type="button"
                      >
                        Save date
                      </button>
                    ) : null}
                  </label>
                </div>
                <strong>{money(selected.total)}</strong>
              </div>
            </div>
            {editable ? (
              <form
                className="grid gap-3 rounded-2xl bg-white p-5 md:grid-cols-4"
                onSubmit={addLine}
              >
                <select
                  className="rounded-xl border p-3 md:col-span-2"
                  name="product_code"
                  required
                >
                  <option value="">Add model</option>
                  {models.map((model) => (
                    <option key={model.product_code} value={model.product_code}>
                      {model.model_identifier} — {model.name}
                    </option>
                  ))}
                </select>
                <input
                  className="rounded-xl border p-3"
                  min="1"
                  name="quantity"
                  placeholder="Qty"
                  required
                  step="1"
                  type="number"
                />
                <button className="rounded-xl bg-blue-900 px-4 font-bold text-white">
                  Add
                </button>
              </form>
            ) : null}
            <div className="space-y-3">
              {selected.line_items.map((line) => (
                <form
                  className="grid gap-3 rounded-2xl bg-white p-4 md:grid-cols-[2fr_100px_1fr_auto_auto]"
                  key={line.id}
                  onSubmit={(event) => void updateLine(line.id, event)}
                >
                  <input
                    name="product_code"
                    type="hidden"
                    value={line.product_code}
                  />
                  <div>
                    <strong>{line.model_identifier}</strong>
                    <span className="block text-sm text-slate-500">
                      {line.product_name}
                    </span>
                  </div>
                  <input
                    className="rounded-lg border p-2"
                    defaultValue={line.quantity}
                    disabled={!editable}
                    min="1"
                    name="quantity"
                    step="1"
                    type="number"
                  />
                  <input
                    className="rounded-lg border p-2"
                    defaultValue={line.notes ?? ""}
                    disabled={!editable}
                    name="notes"
                    placeholder="Notes"
                  />
                  {editable ? (
                    <button className="rounded-lg border px-3 font-semibold">
                      Save
                    </button>
                  ) : null}
                  {editable ? (
                    <button
                      className="rounded-lg bg-yellow-400 px-3 font-semibold text-slate-950"
                      onClick={(event) => {
                        event.preventDefault();
                        void run(async () => {
                          const item =
                            mode === "vendor"
                              ? await deleteVendorRequestLine(
                                  selected.id,
                                  line.id,
                                )
                              : await deletePurchasingRequestLine(
                                  selected.id,
                                  line.id,
                                );
                          setSelected(item);
                          await load();
                        });
                      }}
                      type="button"
                    >
                      Remove
                    </button>
                  ) : null}
                </form>
              ))}
            </div>
            {mode === "vendor" && selected.status === "vendor_draft" ? (
              <div className="flex flex-wrap gap-3">
                <button
                  className="rounded-xl bg-yellow-400 px-5 py-3 font-bold text-slate-950"
                  onClick={() =>
                    void run(async () => {
                      await submitVendorOrderRequest(selected.id);
                      await load();
                      setNotice("Request submitted to Purchasing.");
                    })
                  }
                >
                  Submit to Purchasing
                </button>
                <button
                  className="rounded-xl bg-red-700 px-5 py-3 font-bold text-white"
                  onClick={() => {
                    if (!window.confirm("Delete this unsubmitted order draft?"))
                      return;
                    void run(async () => {
                      await deleteVendorOrderRequest(selected.id);
                      setSelected(null);
                      await load();
                      setNotice("Order draft deleted.");
                    });
                  }}
                  type="button"
                >
                  Delete draft
                </button>
              </div>
            ) : null}
            {mode === "purchasing" ? (
              <div className="flex gap-3">
                <button
                  className="rounded-xl bg-green-700 px-5 py-3 font-bold text-white"
                  disabled={!approvalExpectedDate}
                  onClick={() =>
                    void run(async () => {
                      await decidePurchasingRequest(
                        selected.id,
                        "approve",
                        undefined,
                        approvalExpectedDate,
                      );
                      setSelected(null);
                      await load();
                      setNotice(
                        "Request approved and PO created for vendor acceptance.",
                      );
                    })
                  }
                >
                  Approve and create PO
                </button>
                <button
                  className="rounded-xl bg-red-700 px-5 py-3 font-bold text-white"
                  onClick={() => {
                    const reason = window.prompt("Cancellation reason:") ?? "";
                    if (reason)
                      void run(async () => {
                        await decidePurchasingRequest(
                          selected.id,
                          "cancel",
                          reason,
                        );
                        setSelected(null);
                        await load();
                      });
                  }}
                >
                  Cancel request
                </button>
              </div>
            ) : null}
          </section>
        ) : null}
      </div>
    </main>
  );
}
