"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { completeLifecyclePO } from "@/lib/order-lifecycle-api";
import {
  getReconciliationPurchaseOrder,
  listReconciliationPurchaseOrders,
  PurchaseOrder,
} from "@/lib/purchase-order-api";
import {
  emptyPurchaseOrderFilters,
  PurchaseOrderFilters,
} from "@/components/PurchaseOrderFilters";

const money = (value: string, currency: string) =>
  new Intl.NumberFormat("en-US", { style: "currency", currency }).format(
    Number(value),
  );

export function ReconciliationPurchaseOrderWorkspace() {
  const [queue, setQueue] = useState<"active" | "completed">("active");
  const [orders, setOrders] = useState<PurchaseOrder[]>([]);
  const [selected, setSelected] = useState<PurchaseOrder | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [filters, setFilters] = useState(emptyPurchaseOrderFilters);
  const load = useCallback(
    async () =>
      setOrders(await listReconciliationPurchaseOrders(queue, filters)),
    [filters, queue],
  );
  useEffect(() => {
    void load().catch((caught: unknown) =>
      setError(
        caught instanceof Error
          ? caught.message
          : "Unable to load reconciliation POs.",
      ),
    );
  }, [load]);

  if (selected)
    return (
      <main className="mx-auto max-w-7xl p-4 sm:p-8">
        <button
          className="text-sm text-slate-600"
          onClick={() => setSelected(null)}
        >
          ← Reconciliation PO queue
        </button>
        <header className="mt-4 flex justify-between gap-4">
          <div>
            <p className="brand-eyebrow">Reconciliation custody</p>
            <h1 className="text-3xl font-bold">{selected.po_number}</h1>
            <p className="text-slate-600">{selected.vendor_code}</p>
          </div>
          <div className="text-right">
            <span className="rounded-full bg-yellow-100 px-3 py-1 text-sm font-semibold">
              {queue === "active" ? "Awaiting reconciliation" : "Reconciled"}
            </span>
            <p className="mt-2 text-2xl font-bold">
              {money(selected.total, selected.currency)}
            </p>
          </div>
        </header>
        <section className="mt-6 rounded-2xl bg-white p-6">
          <h2 className="text-xl font-bold">PO lines</h2>
          <div className="mt-4 overflow-x-auto">
            <table className="w-full min-w-[700px] text-left text-sm">
              <thead>
                <tr className="border-b">
                  <th className="py-2">Store</th>
                  <th>Product</th>
                  <th>Quantity</th>
                  <th>Unit cost</th>
                  <th>Extended</th>
                </tr>
              </thead>
              <tbody>
                {selected.lines.map((line) => (
                  <tr className="border-b" key={line.id}>
                    <td className="py-3">{line.store_number}</td>
                    <td>
                      {line.model_identifier} — {line.product_name}
                    </td>
                    <td>{line.quantity}</td>
                    <td>{money(line.unit_price, selected.currency)}</td>
                    <td>{money(line.extended_amount, selected.currency)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <Link
            className="mt-5 inline-block rounded-xl bg-blue-900 px-4 py-3 font-bold text-white"
            href="/invoices"
          >
            Open invoice reconciliation
          </Link>
          {queue === "active" ? (
            <button
              className="ml-3 rounded-xl bg-green-700 px-4 py-3 font-bold text-white"
              onClick={() =>
                void completeLifecyclePO(selected.id).then(() => {
                  setSelected(null);
                  void load();
                })
              }
            >
              Mark reconciled and close PO
            </button>
          ) : null}
        </section>
      </main>
    );

  return (
    <main className="mx-auto max-w-6xl p-4 sm:p-8">
      <Link className="text-sm text-slate-600" href="/">
        ← Command center
      </Link>
      <p className="brand-eyebrow mt-4">Reconciliation custody</p>
      <h1 className="mt-2 text-3xl font-bold">Reconciliation PO database</h1>
      <p className="mt-2 text-slate-600">
        Delivered POs transferred out of Purchasing and awaiting reconciliation
        work.
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
          className={`rounded-xl px-4 py-2 font-bold ${queue === "active" ? "bg-yellow-400 text-slate-950" : "bg-white"}`}
          onClick={() => {
            setQueue("active");
            setSelected(null);
          }}
        >
          Active reconciliation
        </button>
        <button
          className={`rounded-xl px-4 py-2 font-bold ${queue === "completed" ? "bg-yellow-400 text-slate-950" : "bg-white"}`}
          onClick={() => {
            setQueue("completed");
            setSelected(null);
          }}
        >
          Reconciled history
        </button>
      </div>
      <section className="mt-6 overflow-hidden rounded-2xl bg-white">
        {orders.length ? (
          orders.map((order) => (
            <button
              className="flex w-full items-center justify-between border-b p-4 text-left hover:bg-slate-50"
              key={order.id}
              onClick={() =>
                queue === "active"
                  ? void getReconciliationPurchaseOrder(order.id).then(
                      setSelected,
                    )
                  : setSelected(order)
              }
            >
              <span>
                <strong>{order.po_number}</strong>
                <small className="ml-3 text-slate-500">
                  {order.vendor_code}
                </small>
              </span>
              <span>{money(order.total, order.currency)}</span>
            </button>
          ))
        ) : (
          <p className="p-8 text-center text-slate-500">
            No POs are in this queue.
          </p>
        )}
      </section>
    </main>
  );
}
