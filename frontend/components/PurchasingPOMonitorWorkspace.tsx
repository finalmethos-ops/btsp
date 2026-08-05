"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import {
  acknowledgePurchasingPOAttention,
  handoffLifecyclePO,
  listPurchasingLifecyclePOs,
  receiveLifecyclePOLine,
  removeAttentionModel,
  requestPurchasingPOChange,
} from "@/lib/order-lifecycle-api";
import { PurchaseOrder } from "@/lib/purchase-order-api";
import {
  emptyPurchaseOrderFilters,
  PurchaseOrderFilters,
} from "@/components/PurchaseOrderFilters";

const money = (value: string, currency: string) =>
  new Intl.NumberFormat("en-US", { style: "currency", currency }).format(
    Number(value),
  );

const attentionTitle = (action: string) =>
  ({
    out_of_stock: "Out-of-stock units",
    backorder: "Backordered units",
  })[action] ?? action.replaceAll("_", " ");

export function PurchasingPOMonitorWorkspace({
  initialQueue = "active",
}: {
  initialQueue?: "active" | "attention";
}) {
  const [queue, setQueue] = useState<"active" | "attention" | "rejected">(
    initialQueue,
  );
  const [orders, setOrders] = useState<PurchaseOrder[]>([]);
  const [selected, setSelected] = useState<PurchaseOrder | null>(null);
  const [changeDate, setChangeDate] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [filters, setFilters] = useState(emptyPurchaseOrderFilters);
  const load = useCallback(async () => {
    const next = await listPurchasingLifecyclePOs(queue, filters);
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
  return (
    <main className="mx-auto max-w-7xl p-4 sm:p-8">
      <Link className="text-sm text-slate-600" href="/">
        ← Command center
      </Link>
      <p className="brand-eyebrow mt-4">Purchasing custody</p>
      <h1 className="mt-2 text-3xl font-bold">PO Review</h1>
      <p className="mt-2 text-slate-600">
        Monitor accepted POs, record item receipts, review rejected history, and
        hand complete work to Reconciliation.
      </p>
      {error ? (
        <p className="mt-4 rounded-xl bg-red-50 p-3 text-red-800">{error}</p>
      ) : null}
      <PurchaseOrderFilters
        includeVendor
        value={filters}
        onChange={setFilters}
      />
      <div className="mt-5 flex gap-2">
        <button
          className={`rounded-xl px-4 py-2 font-bold ${queue === "attention" ? "bg-yellow-400 text-slate-950" : "bg-white"}`}
          onClick={() => setQueue("attention")}
        >
          Needs Attention
        </button>
        <button
          className={`rounded-xl px-4 py-2 font-bold ${queue === "active" ? "bg-yellow-400 text-slate-950" : "bg-white"}`}
          onClick={() => setQueue("active")}
        >
          Active POs
        </button>
        <button
          className={`rounded-xl px-4 py-2 font-bold ${queue === "rejected" ? "bg-yellow-400 text-slate-950" : "bg-white"}`}
          onClick={() => setQueue("rejected")}
        >
          Rejected POs
        </button>
      </div>
      <div className="mt-5 grid gap-5 lg:grid-cols-[300px_1fr]">
        <section className="rounded-2xl bg-white p-3">
          {orders.map((order) => (
            <button
              className={`mb-2 w-full rounded-xl border p-3 text-left ${selected?.id === order.id ? "selected-object" : ""}`}
              key={order.id}
              onClick={() => setSelected(order)}
            >
              <strong>{order.po_number}</strong>
              <span
                className={`block text-xs ${
                  selected?.id === order.id
                    ? "font-bold !text-slate-950"
                    : "text-slate-500"
                }`}
              >
                {order.vendor_code} · ETA {order.vendor_eta ?? "—"}
              </span>
            </button>
          ))}
          {!orders.length ? (
            <p className="p-5 text-sm text-slate-500">No POs in this queue.</p>
          ) : null}
        </section>
        {selected ? (
          <section className="rounded-2xl bg-white p-6">
            <div className="flex justify-between">
              <div>
                <h2 className="text-2xl font-bold">{selected.po_number}</h2>
                <p className="text-slate-500">{selected.vendor_code}</p>
              </div>
              <strong>{money(selected.total, selected.currency)}</strong>
            </div>
            {queue === "rejected" ? (
              <p className="mt-5 rounded-xl bg-red-50 p-4 text-red-800">
                Vendor rejection: {selected.vendor_rejection_reason}
              </p>
            ) : queue === "attention" ? (
              <div className="mt-5 space-y-4">
                {selected.attention_items
                  .filter((item) => item.status === "pending")
                  .map((item) => (
                    <div
                      className="rounded-xl border border-yellow-500 bg-yellow-200 p-5 text-slate-950"
                      key={item.id}
                    >
                      <div className="flex flex-wrap items-start justify-between gap-2">
                        <div>
                          <p className="text-xs font-bold uppercase tracking-wide text-slate-700">
                            Vendor fulfillment exception
                          </p>
                          <h3 className="mt-1 text-lg font-bold capitalize text-slate-950">
                            {attentionTitle(item.action_type)}
                          </h3>
                        </div>
                        <span className="rounded-full bg-slate-950 px-3 py-1 text-xs font-bold text-white">
                          Needs review
                        </span>
                      </div>
                      <dl className="mt-4 grid gap-3 rounded-xl bg-white/80 p-4 text-sm sm:grid-cols-2">
                        <div>
                          <dt className="font-semibold text-slate-600">
                            Model
                          </dt>
                          <dd className="font-bold text-slate-950">
                            {String(item.payload.product_code ?? "—")}
                          </dd>
                        </div>
                        <div>
                          <dt className="font-semibold text-slate-600">
                            Affected units
                          </dt>
                          <dd className="font-bold text-slate-950">
                            {String(item.payload.quantity ?? "—")}
                          </dd>
                        </div>
                        <div>
                          <dt className="font-semibold text-slate-600">
                            Unit ETA
                          </dt>
                          <dd className="font-bold text-slate-950">
                            {String(item.payload.eta ?? "Not provided")}
                          </dd>
                        </div>
                        <div>
                          <dt className="font-semibold text-slate-600">
                            Suggested substitute
                          </dt>
                          <dd className="font-bold text-slate-950">
                            {item.payload.substitute_product_code ? (
                              <>
                                {String(item.payload.substitute_product_code)}
                                {item.payload.substitute_product_name
                                  ? ` — ${String(item.payload.substitute_product_name)}`
                                  : ""}
                                {item.payload.substitute_unit_price
                                  ? ` ($${Number(item.payload.substitute_unit_price).toFixed(2)})`
                                  : ""}
                              </>
                            ) : (
                              "None suggested"
                            )}
                          </dd>
                        </div>
                      </dl>
                      {item.reason ? (
                        <div className="mt-3 rounded-lg bg-white/80 p-3 text-sm text-slate-950">
                          <strong>Vendor note:</strong> {item.reason}
                        </div>
                      ) : null}
                      <button
                        className="mt-3 rounded-lg bg-blue-900 px-4 py-2 font-bold text-white"
                        onClick={() =>
                          void acknowledgePurchasingPOAttention(
                            selected.id,
                            item.id,
                          ).then(() => {
                            setSelected(null);
                            void load();
                          })
                        }
                      >
                        Approve vendor change and request confirmation
                      </button>
                      {["backorder", "out_of_stock"].includes(
                        item.action_type,
                      ) ? (
                        <button
                          className="ml-2 mt-3 rounded-lg bg-yellow-400 px-4 py-2 font-bold text-slate-950"
                          onClick={() => {
                            if (
                              !window.confirm(
                                "Remove all unreceived units for this model? The PO will be rechecked against every MOQ rule.",
                              )
                            )
                              return;
                            setError(null);
                            void removeAttentionModel(selected.id, item.id)
                              .then(() => {
                                setSelected(null);
                                void load();
                              })
                              .catch((caught: unknown) =>
                                setError(
                                  caught instanceof Error
                                    ? caught.message
                                    : "Unable to remove the model.",
                                ),
                              );
                          }}
                        >
                          Remove model and request vendor confirmation
                        </button>
                      ) : null}
                    </div>
                  ))}
              </div>
            ) : (
              <>
                <div className="mt-5 space-y-2">
                  {selected.lines.map((line) => (
                    <div
                      className="grid items-center gap-3 rounded-xl border p-3 sm:grid-cols-[1fr_auto_auto]"
                      key={line.id}
                    >
                      <div>
                        <strong>
                          {line.product_code} — {line.product_name}
                        </strong>
                        <span className="block text-sm text-slate-500">
                          Received {line.received_quantity} of {line.quantity} ·
                          expected {selected.expected_delivery_date ?? "—"}
                        </span>
                      </div>
                      <input
                        className="w-24 rounded-lg border p-2"
                        defaultValue="1"
                        id={`receive-${line.id}`}
                        min="1"
                        step="1"
                        type="number"
                      />
                      <button
                        className="rounded-lg border px-3 py-2 font-semibold"
                        disabled={
                          Number(line.received_quantity) >=
                          Number(line.quantity)
                        }
                        onClick={() => {
                          const input = document.getElementById(
                            `receive-${line.id}`,
                          ) as HTMLInputElement;
                          void receiveLifecyclePOLine(
                            selected.id,
                            line.id,
                            Number(input.value),
                          ).then((updated) => {
                            setSelected(updated);
                            void load();
                          });
                        }}
                      >
                        Mark received
                      </button>
                    </div>
                  ))}
                </div>
                <button
                  className="mt-5 rounded-xl bg-yellow-400 px-5 py-3 font-bold text-slate-950"
                  onClick={() =>
                    void handoffLifecyclePO(selected.id).then(() => {
                      setSelected(null);
                      void load();
                    })
                  }
                >
                  Hand off to Reconciliation
                </button>
                <div className="mt-5 border-t pt-5">
                  <h3 className="font-bold">Request PO change</h3>
                  <label className="mt-3 block text-sm font-semibold">
                    Requested shipment date for delay or expedite
                    <input
                      className="ml-3 rounded-lg border p-2"
                      onChange={(event) => setChangeDate(event.target.value)}
                      onClick={(event) => event.currentTarget.showPicker()}
                      type="date"
                      value={changeDate}
                    />
                  </label>
                  <div className="mt-3 flex flex-wrap gap-2">
                    {[
                      ["cancel", "Cancel PO"],
                      ["add_model", "Add model"],
                      ["remove_units", "Remove units"],
                      ["delay", "Delay shipment"],
                      ["expedite", "Expedite shipment"],
                      ["request_eta", "Request ETA update"],
                    ].map(([action, label]) => (
                      <button
                        className="rounded-lg border px-3 py-2 font-semibold"
                        key={action}
                        onClick={() => {
                          const reason =
                            window.prompt(
                              `Reason for ${label.toLowerCase()}:`,
                            ) ?? "";
                          if (!reason) return;
                          const payload: Parameters<
                            typeof requestPurchasingPOChange
                          >[1] = {
                            action: action as Parameters<
                              typeof requestPurchasingPOChange
                            >[1]["action"],
                            reason,
                          };
                          if (action === "add_model") {
                            payload.product_code =
                              window.prompt("Model code to add:") ?? "";
                            payload.quantity = Number(
                              window.prompt("Quantity to add:", "1"),
                            );
                          }
                          if (action === "remove_units") {
                            payload.line_id = Number(
                              window.prompt("PO line ID to reduce:"),
                            );
                            payload.quantity = Number(
                              window.prompt("Quantity to remove:", "1"),
                            );
                          }
                          if (action === "delay" || action === "expedite") {
                            if (!changeDate) {
                              setError(
                                "Select a requested shipment date first.",
                              );
                              return;
                            }
                            payload.requested_date = changeDate;
                          }
                          void requestPurchasingPOChange(
                            selected.id,
                            payload,
                          ).then(() => {
                            setSelected(null);
                            void load();
                          });
                        }}
                        type="button"
                      >
                        {label}
                      </button>
                    ))}
                  </div>
                </div>
              </>
            )}
          </section>
        ) : null}
      </div>
    </main>
  );
}
