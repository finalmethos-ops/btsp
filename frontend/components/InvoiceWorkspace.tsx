"use client";

import Link from "next/link";
import { FormEvent, useCallback, useEffect, useState } from "react";
import { createInvoice, listInvoices, VendorInvoice } from "@/lib/invoice-api";
import { listPurchaseOrders, PurchaseOrder } from "@/lib/purchase-order-api";
import {
  createReconciliation,
  decideReconciliation,
  listReconciliations,
  Reconciliation,
  resolveReconciliationException,
} from "@/lib/reconciliation-api";

export function InvoiceWorkspace() {
  const [orders, setOrders] = useState<PurchaseOrder[]>([]);
  const [invoices, setInvoices] = useState<VendorInvoice[]>([]);
  const [reconciliations, setReconciliations] = useState<Reconciliation[]>([]);
  const [orderId, setOrderId] = useState("");
  const [invoiceNumber, setInvoiceNumber] = useState("");
  const [quantities, setQuantities] = useState<Record<number, string>>({});
  const [prices, setPrices] = useState<Record<number, string>>({});
  const [message, setMessage] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    const [nextOrders, nextInvoices, nextCases] = await Promise.all([
      listPurchaseOrders(),
      listInvoices(),
      listReconciliations(),
    ]);
    const eligible = nextOrders.filter(
      (order) => !["created", "prepared", "cancelled"].includes(order.status),
    );
    setOrders(eligible);
    setInvoices(nextInvoices);
    setReconciliations(nextCases);
    setOrderId((current) => current || eligible[0]?.id || "");
  }, []);

  useEffect(() => {
    void load().catch((error: unknown) =>
      setMessage(
        error instanceof Error ? error.message : "Unable to load invoices",
      ),
    );
  }, [load]);

  const order = orders.find((item) => item.id === orderId);

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!order) return;
    const lines = order.lines.map((line, index) => {
      const quantity = Number(quantities[line.id] ?? line.quantity);
      const unitPrice = Number(prices[line.id] ?? line.unit_price);
      return {
        line_number: index + 1,
        purchase_order_line_id: line.id,
        product_code: line.product_code,
        quantity,
        unit_price: unitPrice,
        extended_amount: (quantity * unitPrice).toFixed(4),
      };
    });
    const subtotal = lines
      .reduce((sum, line) => sum + Number(line.extended_amount), 0)
      .toFixed(4);
    setBusy(true);
    setMessage(null);
    try {
      const invoice = await createInvoice({
        invoice_number: invoiceNumber,
        vendor_code: order.vendor_code,
        purchase_order_id: order.id,
        invoice_date: new Date().toISOString(),
        currency: order.currency,
        subtotal,
        freight_total: 0,
        tax_total: 0,
        total: subtotal,
        lines,
      });
      setMessage(
        `${invoice.invoice_number} imported with status ${invoice.status}.`,
      );
      setInvoiceNumber("");
      await load();
    } catch (error) {
      setMessage(
        error instanceof Error
          ? error.message
          : "Invoice could not be imported",
      );
    } finally {
      setBusy(false);
    }
  }

  async function run(action: () => Promise<unknown>, success: string) {
    setBusy(true);
    setMessage(null);
    try {
      await action();
      await load();
      setMessage(success);
    } catch (error) {
      setMessage(
        error instanceof Error
          ? error.message
          : "Reconciliation operation failed",
      );
    } finally {
      setBusy(false);
    }
  }

  function resolveException(exceptionId: string, disposition: string) {
    const note = window.prompt("Exception disposition note:");
    if (!note?.trim()) return;
    void run(
      () =>
        resolveReconciliationException(exceptionId, disposition, note.trim()),
      "Exception disposition recorded.",
    );
  }

  function decide(caseItem: Reconciliation, action: "approve" | "reject") {
    const note = window.prompt(
      `${action === "approve" ? "Approval" : "Rejection"} note:`,
    );
    if (!note?.trim()) return;
    void run(
      () => decideReconciliation(caseItem.id, action, note.trim()),
      `Reconciliation ${action === "approve" ? "approved" : "rejected"}.`,
    );
  }

  return (
    <main className="mx-auto max-w-7xl p-8">
      <header className="mb-8">
        <Link className="text-sm text-blue-700" href="/">
          ← Dashboard
        </Link>
        <h1 className="mt-2 text-3xl font-bold">Vendor Invoices</h1>
        <p className="mt-1 text-slate-600">
          Import invoices and compare vendor claims with ordered and accepted
          quantities.
        </p>
      </header>
      {message ? (
        <p className="mb-6 rounded bg-slate-100 p-3 text-sm">{message}</p>
      ) : null}
      {reconciliations.length ? (
        <section className="mb-6 rounded-lg bg-white p-5 shadow">
          <h2 className="text-xl font-semibold">Reconciliation cases</h2>
          <div className="mt-4 space-y-4">
            {reconciliations.map((caseItem) => (
              <article className="rounded border p-4" key={caseItem.id}>
                <div className="flex items-center justify-between gap-3">
                  <p className="font-medium">
                    Invoice{" "}
                    {invoices.find(
                      (invoice) => invoice.id === caseItem.invoice_id,
                    )?.invoice_number ?? caseItem.invoice_id}
                  </p>
                  <span>{caseItem.status.replaceAll("_", " ")}</span>
                </div>
                {caseItem.exceptions
                  .filter((item) => item.status === "open")
                  .map((item) => (
                    <div
                      className="mt-3 flex flex-wrap items-center gap-3 rounded bg-amber-50 p-3 text-sm"
                      key={item.id}
                    >
                      <span className="font-medium">
                        {item.exception_type.replaceAll("_", " ")}
                      </span>
                      <span>
                        {item.expected_amount} expected / {item.actual_amount}{" "}
                        actual
                      </span>
                      <button
                        className="text-blue-700"
                        disabled={busy}
                        onClick={() =>
                          resolveException(item.id, "accept_variance")
                        }
                        type="button"
                      >
                        Accept variance
                      </button>
                      <button
                        className="text-violet-700"
                        disabled={busy}
                        onClick={() =>
                          resolveException(item.id, "vendor_credit")
                        }
                        type="button"
                      >
                        Request credit
                      </button>
                    </div>
                  ))}
                <div className="mt-3 space-x-3">
                  {caseItem.status === "ready_for_approval" ? (
                    <button
                      className="text-green-700"
                      disabled={busy}
                      onClick={() => decide(caseItem, "approve")}
                      type="button"
                    >
                      Approve for payment
                    </button>
                  ) : null}
                  {!["approved", "rejected"].includes(caseItem.status) ? (
                    <button
                      className="text-red-700"
                      disabled={busy}
                      onClick={() => decide(caseItem, "reject")}
                      type="button"
                    >
                      Reject invoice
                    </button>
                  ) : null}
                </div>
              </article>
            ))}
          </div>
        </section>
      ) : null}
      <section className="grid gap-6 lg:grid-cols-[3fr_2fr]">
        <form className="rounded-lg bg-white p-6 shadow" onSubmit={submit}>
          <h2 className="text-xl font-semibold">Import invoice</h2>
          <label className="mt-4 block text-sm font-medium">
            Purchase order
            <select
              className="mt-1 w-full rounded border p-2"
              onChange={(event) => setOrderId(event.target.value)}
              value={orderId}
            >
              {orders.map((item) => (
                <option key={item.id} value={item.id}>
                  {item.po_number} — {item.vendor_code}
                </option>
              ))}
            </select>
          </label>
          <label className="mt-4 block text-sm font-medium">
            Invoice number
            <input
              className="mt-1 w-full rounded border p-2"
              onChange={(event) => setInvoiceNumber(event.target.value)}
              required
              value={invoiceNumber}
            />
          </label>
          <div className="mt-5 overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b">
                  <th className="p-2">Product</th>
                  <th className="p-2">Quantity</th>
                  <th className="p-2">Unit price</th>
                </tr>
              </thead>
              <tbody>
                {order?.lines.map((line) => (
                  <tr className="border-b" key={line.id}>
                    <td className="p-2">{line.product_code}</td>
                    <td className="p-2">
                      <input
                        className="w-28 rounded border p-2"
                        min="0.0001"
                        onChange={(event) =>
                          setQuantities((current) => ({
                            ...current,
                            [line.id]: event.target.value,
                          }))
                        }
                        step="0.0001"
                        type="number"
                        value={quantities[line.id] ?? line.quantity}
                      />
                    </td>
                    <td className="p-2">
                      <input
                        className="w-28 rounded border p-2"
                        min="0"
                        onChange={(event) =>
                          setPrices((current) => ({
                            ...current,
                            [line.id]: event.target.value,
                          }))
                        }
                        step="0.0001"
                        type="number"
                        value={prices[line.id] ?? line.unit_price}
                      />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <button
            className="mt-5 rounded bg-blue-700 px-4 py-2 text-white disabled:opacity-50"
            disabled={busy || !order || !invoiceNumber}
            type="submit"
          >
            Import and match
          </button>
        </form>
        <div className="rounded-lg bg-white p-6 shadow">
          <h2 className="text-xl font-semibold">Recent invoices</h2>
          <div className="mt-4 space-y-3">
            {invoices.map((invoice) => (
              <article className="rounded border p-3" key={invoice.id}>
                <div className="flex justify-between gap-3">
                  <p className="font-medium">{invoice.invoice_number}</p>
                  <span
                    className={
                      invoice.status === "matched"
                        ? "text-green-700"
                        : "text-amber-700"
                    }
                  >
                    {invoice.status.replaceAll("_", " ")}
                  </span>
                </div>
                <p className="text-sm text-slate-600">
                  {invoice.vendor_code} · {invoice.currency} {invoice.total}
                </p>
                {invoice.lines.some(
                  (line) => line.match.status === "exception",
                ) ? (
                  <p className="mt-1 text-xs text-amber-700">
                    Line match exception requires reconciliation.
                  </p>
                ) : null}
                {!reconciliations.some(
                  (item) => item.invoice_id === invoice.id,
                ) ? (
                  <button
                    className="mt-2 text-sm text-blue-700"
                    disabled={busy}
                    onClick={() =>
                      void run(
                        () => createReconciliation(invoice.id),
                        "Reconciliation case created.",
                      )
                    }
                    type="button"
                  >
                    Start reconciliation
                  </button>
                ) : null}
              </article>
            ))}
          </div>
        </div>
      </section>
    </main>
  );
}
