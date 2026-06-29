"use client";

import Link from "next/link";
import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import { listPurchaseOrders, PurchaseOrder } from "@/lib/purchase-order-api";
import {
  createReceipt,
  createBackorder,
  listBackorders,
  listOpenVariances,
  listReceipts,
  PurchaseReceipt,
  PurchaseBackorder,
  ReceiptVariance,
  resolveVariance,
  runBackorderAction,
} from "@/lib/receiving-api";

export function ReceivingWorkspace() {
  const [orders, setOrders] = useState<PurchaseOrder[]>([]);
  const [receipts, setReceipts] = useState<PurchaseReceipt[]>([]);
  const [variances, setVariances] = useState<ReceiptVariance[]>([]);
  const [backorders, setBackorders] = useState<PurchaseBackorder[]>([]);
  const [orderId, setOrderId] = useState("");
  const [storeNumber, setStoreNumber] = useState("");
  const [quantities, setQuantities] = useState<Record<number, string>>({});
  const [packingSlip, setPackingSlip] = useState("");
  const [externalId, setExternalId] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    const [nextOrders, nextReceipts, nextVariances, nextBackorders] =
      await Promise.all([
        listPurchaseOrders(),
        listReceipts(),
        listOpenVariances(),
        listBackorders(),
      ]);
    const eligible = nextOrders.filter((order) =>
      [
        "transmitted",
        "vendor_acknowledged",
        "vendor_acknowledged_changes",
        "shipment_planned",
        "shipment_in_transit",
        "shipment_delayed",
        "shipment_delivered",
        "partially_received",
      ].includes(order.status),
    );
    setOrders(eligible);
    setReceipts(nextReceipts);
    setVariances(nextVariances);
    setBackorders(nextBackorders);
    setOrderId((current) => current || eligible[0]?.id || "");
  }, []);

  useEffect(() => {
    void load().catch((error: unknown) =>
      setMessage(
        error instanceof Error ? error.message : "Unable to load receiving",
      ),
    );
  }, [load]);

  const order = orders.find((item) => item.id === orderId);
  const stores = useMemo(
    () => [...new Set(order?.lines.map((line) => line.store_number) ?? [])],
    [order],
  );

  useEffect(() => {
    setStoreNumber(stores[0] ?? "");
    setQuantities({});
  }, [orderId, stores]);

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!order) return;
    const lines = order.lines
      .filter((line) => line.store_number === storeNumber)
      .map((line) => ({ line, quantity: Number(quantities[line.id] ?? 0) }))
      .filter(({ quantity }) => quantity > 0)
      .map(({ line, quantity }) => ({
        purchase_order_line_id: line.id,
        received_quantity: quantity,
        accepted_quantity: quantity,
        rejected_quantity: 0,
      }));
    if (!lines.length) {
      setMessage("Enter a received quantity for at least one line.");
      return;
    }
    setBusy(true);
    setMessage(null);
    try {
      const receipt = await createReceipt({
        purchase_order_id: order.id,
        store_number: storeNumber,
        external_receipt_id: externalId || null,
        packing_slip_number: packingSlip || null,
        received_at: new Date().toISOString(),
        lines,
      });
      setMessage(`${receipt.receipt_number} posted successfully.`);
      setExternalId("");
      setPackingSlip("");
      setQuantities({});
      await load();
    } catch (error) {
      setMessage(
        error instanceof Error ? error.message : "Receipt could not be posted",
      );
    } finally {
      setBusy(false);
    }
  }

  async function closeVariance(
    variance: ReceiptVariance,
    action: "resolve" | "waive",
  ) {
    const note = window.prompt(
      `${action === "resolve" ? "Resolution" : "Waiver"} note for ${variance.variance_type.replaceAll("_", " ")}:`,
    );
    if (!note?.trim()) return;
    setBusy(true);
    setMessage(null);
    try {
      await resolveVariance(variance.id, action, note.trim());
      setMessage(`Variance ${action === "resolve" ? "resolved" : "waived"}.`);
      await load();
    } catch (error) {
      setMessage(
        error instanceof Error
          ? error.message
          : "Variance could not be updated",
      );
    } finally {
      setBusy(false);
    }
  }

  async function openBackorder(variance: ReceiptVariance) {
    const note = window.prompt("Backorder decision note:");
    if (!note?.trim()) return;
    setBusy(true);
    try {
      await createBackorder(variance.id, note.trim());
      setMessage("Backorder created.");
      await load();
    } catch (error) {
      setMessage(
        error instanceof Error
          ? error.message
          : "Backorder could not be created",
      );
    } finally {
      setBusy(false);
    }
  }

  async function actOnBackorder(
    backorder: PurchaseBackorder,
    action: "receive" | "cancel" | "substitute",
  ) {
    const detail =
      action === "receive"
        ? window.prompt("Quantity received:")
        : action === "substitute"
          ? window.prompt("Substitute product code:")
          : null;
    if (action !== "cancel" && !detail?.trim()) return;
    const note = window.prompt(`${action} note:`);
    if (!note?.trim()) return;
    const payload: Record<string, unknown> = { action, note: note.trim() };
    if (action === "receive") payload.quantity = Number(detail);
    if (action === "substitute")
      payload.substitute_product_code = detail?.trim();
    setBusy(true);
    try {
      await runBackorderAction(backorder.id, payload);
      setMessage(`Backorder ${action} recorded.`);
      await load();
    } catch (error) {
      setMessage(
        error instanceof Error
          ? error.message
          : "Backorder could not be updated",
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="mx-auto max-w-7xl p-8">
      <header className="mb-8">
        <Link className="text-sm text-blue-700" href="/">
          ← Dashboard
        </Link>
        <h1 className="mt-2 text-3xl font-bold">Receiving</h1>
        <p className="mt-1 text-slate-600">
          Post physical receipts against eligible purchase orders.
        </p>
      </header>
      {message ? (
        <p className="mb-6 rounded bg-slate-100 p-3 text-sm">{message}</p>
      ) : null}
      {variances.length ? (
        <section className="mb-6 rounded-lg border border-amber-300 bg-amber-50 p-5">
          <h2 className="text-lg font-semibold">
            Open receiving variances ({variances.length})
          </h2>
          <div className="mt-3 overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b border-amber-300">
                  <th className="p-2">Type</th>
                  <th className="p-2">Expected</th>
                  <th className="p-2">Actual</th>
                  <th className="p-2">Difference</th>
                  <th className="p-2"></th>
                </tr>
              </thead>
              <tbody>
                {variances.map((variance) => (
                  <tr className="border-b border-amber-200" key={variance.id}>
                    <td className="p-2 font-medium">
                      {variance.variance_type.replaceAll("_", " ")}
                    </td>
                    <td className="p-2">{variance.expected_quantity}</td>
                    <td className="p-2">{variance.actual_quantity}</td>
                    <td className="p-2">{variance.difference_quantity}</td>
                    <td className="space-x-3 p-2">
                      {["asn_shortage", "rejected_quantity"].includes(
                        variance.variance_type,
                      ) ? (
                        <button
                          className="text-amber-800 disabled:opacity-50"
                          disabled={busy}
                          onClick={() => void openBackorder(variance)}
                          type="button"
                        >
                          Backorder
                        </button>
                      ) : null}
                      <button
                        className="text-blue-700 disabled:opacity-50"
                        disabled={busy}
                        onClick={() => void closeVariance(variance, "resolve")}
                        type="button"
                      >
                        Resolve
                      </button>
                      <button
                        className="text-slate-700 disabled:opacity-50"
                        disabled={busy}
                        onClick={() => void closeVariance(variance, "waive")}
                        type="button"
                      >
                        Waive
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      ) : null}
      {backorders.length ? (
        <section className="mb-6 rounded-lg bg-white p-5 shadow">
          <h2 className="text-lg font-semibold">Backorders</h2>
          <div className="mt-3 overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b">
                  <th className="p-2">Number</th>
                  <th className="p-2">Product</th>
                  <th className="p-2">Status</th>
                  <th className="p-2">Outstanding</th>
                  <th className="p-2"></th>
                </tr>
              </thead>
              <tbody>
                {backorders.map((backorder) => (
                  <tr className="border-b" key={backorder.id}>
                    <td className="p-2 font-medium">
                      {backorder.backorder_number}
                    </td>
                    <td className="p-2">{backorder.product_code}</td>
                    <td className="p-2">
                      {backorder.status.replaceAll("_", " ")}
                    </td>
                    <td className="p-2">{backorder.outstanding_quantity}</td>
                    <td className="space-x-3 p-2">
                      {["open", "partially_fulfilled"].includes(
                        backorder.status,
                      ) ? (
                        <>
                          <button
                            className="text-blue-700"
                            disabled={busy}
                            onClick={() =>
                              void actOnBackorder(backorder, "receive")
                            }
                            type="button"
                          >
                            Receive
                          </button>
                          <button
                            className="text-violet-700"
                            disabled={busy}
                            onClick={() =>
                              void actOnBackorder(backorder, "substitute")
                            }
                            type="button"
                          >
                            Substitute
                          </button>
                          <button
                            className="text-red-700"
                            disabled={busy}
                            onClick={() =>
                              void actOnBackorder(backorder, "cancel")
                            }
                            type="button"
                          >
                            Cancel
                          </button>
                        </>
                      ) : null}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      ) : null}
      <section className="grid gap-6 lg:grid-cols-[3fr_2fr]">
        <form className="rounded-lg bg-white p-6 shadow" onSubmit={submit}>
          <h2 className="text-xl font-semibold">Post receipt</h2>
          <label className="mt-4 block text-sm font-medium">
            Purchase order
          </label>
          <select
            className="mt-1 w-full rounded border p-2"
            onChange={(event) => setOrderId(event.target.value)}
            value={orderId}
          >
            {orders.map((item) => (
              <option key={item.id} value={item.id}>
                {item.po_number} — {item.vendor_code} ({item.status})
              </option>
            ))}
          </select>
          <label className="mt-4 block text-sm font-medium">
            Receiving store
          </label>
          <select
            className="mt-1 w-full rounded border p-2"
            onChange={(event) => setStoreNumber(event.target.value)}
            value={storeNumber}
          >
            {stores.map((store) => (
              <option key={store}>{store}</option>
            ))}
          </select>
          <div className="mt-5 overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b">
                  <th className="p-2">Product</th>
                  <th className="p-2">Ordered</th>
                  <th className="p-2">Received now</th>
                </tr>
              </thead>
              <tbody>
                {order?.lines
                  .filter((line) => line.store_number === storeNumber)
                  .map((line) => (
                    <tr className="border-b" key={line.id}>
                      <td className="p-2">
                        <span className="font-medium">{line.product_code}</span>
                        <br />
                        <span className="text-slate-500">
                          {line.product_name}
                        </span>
                      </td>
                      <td className="p-2">{line.quantity}</td>
                      <td className="p-2">
                        <input
                          className="w-28 rounded border p-2"
                          min="0"
                          onChange={(event) =>
                            setQuantities((current) => ({
                              ...current,
                              [line.id]: event.target.value,
                            }))
                          }
                          step="0.0001"
                          type="number"
                          value={quantities[line.id] ?? ""}
                        />
                      </td>
                    </tr>
                  ))}
              </tbody>
            </table>
          </div>
          <div className="mt-5 grid gap-4 sm:grid-cols-2">
            <label className="text-sm font-medium">
              Packing slip
              <input
                className="mt-1 w-full rounded border p-2"
                onChange={(event) => setPackingSlip(event.target.value)}
                value={packingSlip}
              />
            </label>
            <label className="text-sm font-medium">
              External receipt ID
              <input
                className="mt-1 w-full rounded border p-2"
                onChange={(event) => setExternalId(event.target.value)}
                value={externalId}
              />
            </label>
          </div>
          <button
            className="mt-5 rounded bg-blue-700 px-4 py-2 text-white disabled:opacity-50"
            disabled={busy || !order || !storeNumber}
            type="submit"
          >
            Post receipt
          </button>
        </form>
        <div className="rounded-lg bg-white p-6 shadow">
          <h2 className="text-xl font-semibold">Recent receipts</h2>
          <div className="mt-4 space-y-3">
            {receipts.map((receipt) => (
              <article className="rounded border p-3" key={receipt.id}>
                <p className="font-medium">{receipt.receipt_number}</p>
                <p className="text-sm text-slate-600">
                  Store {receipt.store_number} · {receipt.lines.length} line(s)
                </p>
                <p className="text-xs text-slate-500">
                  {new Date(receipt.received_at).toLocaleString()}
                </p>
              </article>
            ))}
          </div>
        </div>
      </section>
    </main>
  );
}
