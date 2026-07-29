"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import {
  downloadVendorPO,
  getVendorPOEmailDetails,
  listVendorPOs,
  respondToVendorPO,
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

export function VendorPOAcceptanceWorkspace() {
  const [queue, setQueue] = useState<"pending" | "rejected">("pending");
  const [orders, setOrders] = useState<PurchaseOrder[]>([]);
  const [selected, setSelected] = useState<PurchaseOrder | null>(null);
  const [eta, setEta] = useState("");
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
      setError(caught instanceof Error ? caught.message : "Unable to load POs"),
    );
  }, [load]);
  async function printPO() {
    if (!selected) return;
    const blob = await downloadVendorPO(selected.id);
    const url = URL.createObjectURL(blob);
    window.open(url, "_blank");
    window.setTimeout(() => URL.revokeObjectURL(url), 60_000);
  }
  async function emailPO() {
    if (!selected) return;
    const [details, blob] = await Promise.all([
      getVendorPOEmailDetails(selected.id),
      downloadVendorPO(selected.id),
    ]);
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `${selected.po_number}.pdf`;
    anchor.click();
    URL.revokeObjectURL(url);
    window.location.href = `mailto:${encodeURIComponent(details.recipient ?? "")}?subject=${encodeURIComponent(details.subject)}&body=${encodeURIComponent(`${details.body}\n\nThe PO PDF has been downloaded for attachment.`)}`;
  }
  return (
    <main className="mx-auto max-w-7xl p-4 sm:p-8">
      <Link className="text-sm text-slate-600" href="/">
        ← Command center
      </Link>
      <p className="brand-eyebrow mt-4">Vendor response</p>
      <h1 className="mt-2 text-3xl font-bold">Accept PO</h1>
      <p className="mt-2 text-slate-600">
        Print or prepare an email copy, then accept with an ETA or reject with a
        reason. PO content is locked.
      </p>
      {error ? (
        <p className="mt-4 rounded-xl bg-red-50 p-3 text-red-800">{error}</p>
      ) : null}
      <PurchaseOrderFilters value={filters} onChange={setFilters} />
      <div className="mt-5 flex gap-2">
        <button
          className={`rounded-xl px-4 py-2 font-bold ${queue === "pending" ? "bg-yellow-400 text-slate-950" : "bg-white"}`}
          onClick={() => setQueue("pending")}
        >
          Awaiting response
        </button>
        <button
          className={`rounded-xl px-4 py-2 font-bold ${queue === "rejected" ? "bg-yellow-400 text-slate-950" : "bg-white"}`}
          onClick={() => setQueue("rejected")}
        >
          Rejected history
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
                className={`block text-sm ${
                  selected?.id === order.id
                    ? "font-bold !text-slate-950"
                    : "text-slate-500"
                }`}
              >
                {money(order.total, order.currency)}
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
                <p className="text-slate-500">Locked purchase order</p>
                <p className="mt-2 text-sm font-semibold">
                  Expected delivery: {selected.expected_delivery_date ?? "—"}
                </p>
              </div>
              <strong>{money(selected.total, selected.currency)}</strong>
            </div>
            <div className="mt-5 overflow-x-auto">
              <table className="w-full min-w-[620px] text-left text-sm">
                <thead>
                  <tr className="border-b">
                    <th className="py-2">Store / model</th>
                    <th>Qty</th>
                    <th>Unit</th>
                  </tr>
                </thead>
                <tbody>
                  {selected.lines.map((line) => (
                    <tr className="border-b" key={line.id}>
                      <td className="py-3">
                        {line.store_number} · {line.product_code} —{" "}
                        {line.product_name}
                      </td>
                      <td>{line.quantity}</td>
                      <td>{money(line.unit_price, selected.currency)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="mt-5 flex flex-wrap gap-2">
              <button
                className="rounded-xl border px-4 py-2 font-bold"
                onClick={() => void printPO()}
              >
                Print PDF
              </button>
              <button
                className="rounded-xl border px-4 py-2 font-bold"
                onClick={() => void emailPO()}
              >
                Email copy
              </button>
            </div>
            {queue === "pending" ? (
              <div className="mt-5 border-t pt-5">
                <label className="text-sm font-bold">
                  Estimated delivery date
                  <input
                    className="ml-3 rounded-lg border p-2"
                    min={selected.expected_delivery_date ?? undefined}
                    onChange={(e) => setEta(e.target.value)}
                    onClick={(event) => event.currentTarget.showPicker()}
                    type="date"
                    value={eta}
                  />
                </label>
                <div className="mt-3 flex gap-2">
                  <button
                    className="rounded-xl bg-green-700 px-5 py-3 font-bold text-white"
                    disabled={!eta}
                    onClick={() =>
                      void respondToVendorPO(selected.id, "accept", eta).then(
                        load,
                      )
                    }
                  >
                    Accept PO
                  </button>
                  <button
                    className="rounded-xl bg-red-700 px-5 py-3 font-bold text-white"
                    onClick={() => {
                      const reason =
                        window.prompt("Reason for rejecting this PO:") ?? "";
                      if (reason)
                        void respondToVendorPO(
                          selected.id,
                          "reject",
                          undefined,
                          reason,
                        ).then(load);
                    }}
                  >
                    Reject PO
                  </button>
                </div>
              </div>
            ) : (
              <p className="mt-5 rounded-xl bg-red-50 p-3 text-red-800">
                Rejected: {selected.vendor_rejection_reason}
              </p>
            )}
          </section>
        ) : null}
      </div>
    </main>
  );
}
