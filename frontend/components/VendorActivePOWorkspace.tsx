"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import {
  listVendorSubstituteOptions,
  listVendorPOs,
  reportVendorPOIssue,
  respondVendorPOAttention,
  updateVendorPOEta,
} from "@/lib/order-lifecycle-api";
import { PurchaseOrder } from "@/lib/purchase-order-api";
import { VendorModel } from "@/lib/vendor-model-api";
import {
  emptyPurchaseOrderFilters,
  PurchaseOrderFilters,
} from "@/components/PurchaseOrderFilters";

export function VendorActivePOWorkspace({
  queue,
}: {
  queue: "active" | "attention";
}) {
  const [orders, setOrders] = useState<PurchaseOrder[]>([]);
  const [selected, setSelected] = useState<PurchaseOrder | null>(null);
  const [eta, setEta] = useState("");
  const [substituteOptions, setSubstituteOptions] = useState<
    Record<number, VendorModel[]>
  >({});
  const [selectedSubstitutes, setSelectedSubstitutes] = useState<
    Record<number, string>
  >({});
  const [error, setError] = useState<string | null>(null);
  const [filters, setFilters] = useState(emptyPurchaseOrderFilters);
  const load = useCallback(async () => {
    const next = await listVendorPOs(queue, filters);
    setOrders(next);
    setSelected(
      (current) =>
        next.find((item) => item.id === current?.id) ?? next[0] ?? null,
    );
  }, [filters, queue]);
  useEffect(() => {
    void load().catch((caught: unknown) =>
      setError(
        caught instanceof Error ? caught.message : "Unable to load POs.",
      ),
    );
  }, [load]);
  useEffect(() => {
    if (!selected || queue !== "active") {
      setSubstituteOptions({});
      return;
    }
    void Promise.all(
      selected.lines.map(
        async (line) =>
          [
            line.id,
            await listVendorSubstituteOptions(selected.id, line.id),
          ] as const,
      ),
    ).then((entries) => setSubstituteOptions(Object.fromEntries(entries)));
  }, [queue, selected]);
  async function run(operation: () => Promise<unknown>) {
    setError(null);
    try {
      await operation();
      await load();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Operation failed.");
    }
  }
  return (
    <main className="mx-auto max-w-7xl p-4 sm:p-8">
      <Link className="text-sm text-slate-600" href="/">
        ← Command center
      </Link>
      <p className="brand-eyebrow mt-4">Vendor fulfillment</p>
      <h1 className="mt-2 text-3xl font-bold">
        {queue === "active" ? "Active POs" : "POs Needing Attention"}
      </h1>
      <p className="mt-2 text-slate-600">
        {queue === "active"
          ? "Maintain delivery ETA and report unit-level fulfillment exceptions."
          : "Accept or deny Purchasing change requests and provide requested ETA updates."}
      </p>
      {error ? (
        <p className="mt-4 rounded-xl bg-red-50 p-3 text-red-800">{error}</p>
      ) : null}
      <PurchaseOrderFilters value={filters} onChange={setFilters} />
      <div className="mt-5 grid gap-5 lg:grid-cols-[300px_1fr]">
        <section className="rounded-2xl bg-white p-3">
          {orders.map((order) => (
            <button
              className={`mb-2 w-full rounded-xl border p-3 text-left ${selected?.id === order.id ? "selected-object" : ""}`}
              key={order.id}
              onClick={() => {
                setSelected(order);
                setEta(order.vendor_eta ?? "");
              }}
            >
              <strong>{order.po_number}</strong>
              <span
                className={`block text-xs ${
                  selected?.id === order.id
                    ? "font-bold !text-slate-950"
                    : "text-slate-500"
                }`}
              >
                ETA {order.vendor_eta ?? "—"}
              </span>
            </button>
          ))}
          {!orders.length ? (
            <p className="p-4 text-sm text-slate-500">No POs in this queue.</p>
          ) : null}
        </section>
        {selected ? (
          <section className="rounded-2xl bg-white p-6">
            <h2 className="text-2xl font-bold">{selected.po_number}</h2>
            <p className="text-sm text-slate-500">
              Expected delivery {selected.expected_delivery_date ?? "—"}
            </p>
            {queue === "active" ? (
              <>
                <div className="mt-5 flex flex-wrap items-center gap-3 rounded-xl bg-slate-50 p-4">
                  <label className="font-bold">Global ETA</label>
                  <input
                    className="rounded-lg border p-2"
                    min={selected.expected_delivery_date ?? undefined}
                    onChange={(event) => setEta(event.target.value)}
                    onClick={(event) => event.currentTarget.showPicker()}
                    type="date"
                    value={eta}
                  />
                  <button
                    className="rounded-lg bg-blue-900 px-4 py-2 font-bold text-white"
                    disabled={!eta}
                    onClick={() =>
                      void run(() => updateVendorPOEta(selected.id, eta))
                    }
                  >
                    Update ETA
                  </button>
                </div>
                <div className="mt-4 space-y-3">
                  {selected.lines.map((line) => (
                    <div className="rounded-xl border p-4" key={line.id}>
                      <strong>
                        {line.product_code} — {line.product_name}
                      </strong>
                      <span className="block text-sm text-slate-500">
                        {line.quantity} ordered · {line.received_quantity}{" "}
                        received
                      </span>
                      <div className="mt-3 flex gap-2">
                        <button
                          className="rounded-lg border px-3 py-2 font-semibold"
                          onClick={() => {
                            const quantity = Number(
                              window.prompt("Backordered unit quantity:", "1"),
                            );
                            const unitEta = eta;
                            if (quantity > 0 && unitEta)
                              void run(() =>
                                reportVendorPOIssue(selected.id, {
                                  action: "backorder",
                                  line_id: line.id,
                                  quantity,
                                  eta: unitEta,
                                }),
                              );
                          }}
                        >
                          Mark units backordered using selected ETA
                        </button>
                        <select
                          className="min-w-56 rounded-lg border p-2"
                          onChange={(event) =>
                            setSelectedSubstitutes((current) => ({
                              ...current,
                              [line.id]: event.target.value,
                            }))
                          }
                          value={selectedSubstitutes[line.id] ?? ""}
                        >
                          <option value="">No substitute suggested</option>
                          {(substituteOptions[line.id] ?? []).map((model) => (
                            <option
                              key={model.product_code}
                              value={model.product_code}
                            >
                              {model.model_identifier} — {model.name} ($
                              {Number(model.unit_price).toFixed(2)})
                            </option>
                          ))}
                        </select>
                        <button
                          className="rounded-lg border px-3 py-2 font-semibold"
                          onClick={() => {
                            const quantity = Number(
                              window.prompt("Out-of-stock unit quantity:", "1"),
                            );
                            if (quantity > 0)
                              void run(() =>
                                reportVendorPOIssue(selected.id, {
                                  action: "out_of_stock",
                                  line_id: line.id,
                                  quantity,
                                  substitute_product_code:
                                    selectedSubstitutes[line.id] || null,
                                }),
                              );
                          }}
                        >
                          Mark out of stock and offer substitute
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              </>
            ) : (
              <div className="mt-5 space-y-4">
                {selected.attention_items
                  .filter((item) => item.status === "pending")
                  .map((item) => (
                    <div
                      className="rounded-xl border border-amber-300 bg-amber-50 p-4"
                      key={item.id}
                    >
                      <strong>
                        {item.action_type === "vendor_change_confirmation"
                          ? "Confirm Purchasing PO change"
                          : item.action_type.replaceAll("_", " ")}
                      </strong>
                      <p className="mt-1 text-sm">{item.reason}</p>
                      {item.action_type === "vendor_change_confirmation" ? (
                        <dl className="mt-3 grid gap-2 rounded-lg bg-white p-3 text-sm sm:grid-cols-2">
                          <div>
                            <dt className="font-semibold text-slate-600">
                              Purchasing action
                            </dt>
                            <dd className="font-bold capitalize">
                              {String(
                                item.payload.resolution_action ?? "PO change",
                              ).replaceAll("_", " ")}
                            </dd>
                          </div>
                          <div>
                            <dt className="font-semibold text-slate-600">
                              Approved by
                            </dt>
                            <dd className="font-bold">
                              {String(item.payload.approved_by ?? "Purchasing")}
                            </dd>
                          </div>
                          <div className="sm:col-span-2">
                            <dt className="font-semibold text-slate-600">
                              Applied change details
                            </dt>
                            <dd className="mt-1 whitespace-pre-wrap font-mono text-xs">
                              {JSON.stringify(
                                item.payload.change_details ?? {},
                                null,
                                2,
                              )}
                            </dd>
                          </div>
                        </dl>
                      ) : (
                        <pre className="mt-2 overflow-auto text-xs">
                          {JSON.stringify(item.payload, null, 2)}
                        </pre>
                      )}
                      {item.action_type === "vendor_change_confirmation" ? (
                        <button
                          className="mt-3 rounded-lg bg-yellow-400 px-4 py-2 font-bold text-slate-950"
                          onClick={() =>
                            void run(() =>
                              respondVendorPOAttention(
                                selected.id,
                                item.id,
                                "confirm",
                                undefined,
                                "Vendor confirmed the applied PO change.",
                              ),
                            )
                          }
                        >
                          Confirm PO change
                        </button>
                      ) : (
                        <div className="mt-3 flex flex-wrap gap-2">
                          <input
                            className="rounded-lg border p-2"
                            onChange={(event) => setEta(event.target.value)}
                            onClick={(event) =>
                              event.currentTarget.showPicker()
                            }
                            placeholder="Updated ETA if requested"
                            type="date"
                            value={eta}
                          />
                          <button
                            className="rounded-lg bg-green-700 px-4 py-2 font-bold text-white"
                            onClick={() =>
                              void run(() =>
                                respondVendorPOAttention(
                                  selected.id,
                                  item.id,
                                  "accept",
                                  eta || undefined,
                                ),
                              )
                            }
                          >
                            Accept
                          </button>
                          <button
                            className="rounded-lg bg-red-700 px-4 py-2 font-bold text-white"
                            onClick={() => {
                              const note =
                                window.prompt("Reason for denial:") ?? "";
                              if (note)
                                void run(() =>
                                  respondVendorPOAttention(
                                    selected.id,
                                    item.id,
                                    "deny",
                                    undefined,
                                    note,
                                  ),
                                );
                            }}
                          >
                            Deny
                          </button>
                        </div>
                      )}
                    </div>
                  ))}
              </div>
            )}
          </section>
        ) : null}
      </div>
    </main>
  );
}
