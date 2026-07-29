"use client";

import { useCallback, useEffect, useState } from "react";
import {
  decideEventOrder,
  EventOrderReviewSummary,
  exportEventOrders,
  exportEventOrderBackup,
  getEventOrderReview,
  releaseEventOrders,
} from "@/lib/event-order-review-api";

export function EventOrderReviewPanel({
  eventId,
  readOnly = false,
}: {
  eventId: string;
  readOnly?: boolean;
}) {
  const [summary, setSummary] = useState<EventOrderReviewSummary | null>(null);
  const [quantities, setQuantities] = useState<Record<string, number>>({});
  const [reasons, setReasons] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(() => {
    void getEventOrderReview(eventId)
      .then(setSummary)
      .catch((caught: unknown) =>
        setError(
          caught instanceof Error
            ? caught.message
            : "Review queue could not load",
        ),
      );
  }, [eventId]);

  useEffect(load, [load]);

  async function decide(
    orderId: string,
    decision: "approve" | "reject" | "revise",
  ) {
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      const updated = await decideEventOrder(orderId, {
        decision,
        revised_quantity: decision === "revise" ? quantities[orderId] : null,
        reason: decision === "approve" ? null : reasons[orderId],
      });
      setSummary(updated);
      setMessage(`Order ${decision} decision recorded.`);
    } catch (caught) {
      setError(
        caught instanceof Error ? caught.message : "Decision could not save",
      );
    } finally {
      setBusy(false);
    }
  }

  async function release() {
    setBusy(true);
    setError(null);
    try {
      const batch = await releaseEventOrders(eventId);
      setMessage(
        `Release batch ${batch.batch_id} created ${batch.purchase_request_count} standard purchasing request(s): ${batch.order_count} event orders, ${batch.total_units} units, $${batch.total_spend}.`,
      );
      load();
    } catch (caught) {
      setError(
        caught instanceof Error
          ? caught.message
          : "Release could not be created",
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="event-ui rounded-2xl border p-5">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="brand-eyebrow">020F · Purchasing handoff</p>
          <h3 className="text-xl font-bold">Event order review</h3>
          <p className="text-sm text-slate-600">
            Review live demand, then release model-level lines directly into
            standard purchasing.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          {!readOnly ? (
            <button
              className="rounded-lg border px-3 py-2 font-semibold"
              disabled={busy || !summary}
              onClick={() =>
                summary &&
                void exportEventOrderBackup(eventId, summary.event_name)
              }
              type="button"
            >
              Download all orders (.xlsx)
            </button>
          ) : null}
          <button
            className="rounded-lg border px-3 py-2 font-semibold"
            onClick={() => void exportEventOrders(eventId)}
            type="button"
          >
            Export CSV
          </button>
          <button
            className="rounded-lg bg-blue-800 px-3 py-2 font-semibold text-white"
            disabled={busy || !summary?.approved}
            onClick={() => void release()}
            type="button"
          >
            Release approved to purchasing
          </button>
        </div>
      </div>
      {message ? (
        <p className="mt-3 rounded-lg bg-green-50 p-3 text-green-800">
          {message}
        </p>
      ) : null}
      {error ? (
        <p className="mt-3 rounded-lg bg-red-50 p-3 text-red-800">{error}</p>
      ) : null}
      <div className="mt-4 grid gap-3 sm:grid-cols-4">
        <div className="rounded-xl bg-slate-50 p-3">
          <span className="text-xs">PENDING</span>
          <strong className="block text-2xl">{summary?.pending ?? 0}</strong>
        </div>
        <div className="rounded-xl bg-green-50 p-3">
          <span className="text-xs">APPROVED</span>
          <strong className="block text-2xl">{summary?.approved ?? 0}</strong>
        </div>
        <div className="rounded-xl bg-red-50 p-3">
          <span className="text-xs">REJECTED</span>
          <strong className="block text-2xl">{summary?.rejected ?? 0}</strong>
        </div>
        <div className="rounded-xl bg-blue-50 p-3">
          <span className="text-xs">RELEASED</span>
          <strong className="block text-2xl">{summary?.released ?? 0}</strong>
        </div>
      </div>
      <div className="mt-4 overflow-x-auto">
        <table className="w-full min-w-[1050px] text-left text-sm">
          <thead>
            <tr className="border-b">
              <th className="p-2">Entity</th>
              <th>Product</th>
              <th>Vendor</th>
              <th>Qty</th>
              <th>Total</th>
              <th>Delivery</th>
              <th>Live</th>
              <th>Review</th>
              <th>Decision</th>
            </tr>
          </thead>
          <tbody>
            {summary?.items.map((item) => (
              <tr className="border-b align-top" key={item.order_id}>
                <td className="p-2 font-semibold">{item.entity_code}</td>
                <td>
                  <strong>{item.model_number}</strong>
                  <br />
                  {item.product_name}
                  {item.variant_lines.length > 1 ? (
                    <div className="mt-2 space-y-1 border-t pt-2 text-xs">
                      {item.variant_lines.map((variant) => (
                        <div key={variant.model_number}>
                          <strong>{variant.model_number}</strong> ·{" "}
                          {variant.product_name} · {variant.quantity} × $
                          {variant.unit_cost} = ${variant.total_cost}
                        </div>
                      ))}
                    </div>
                  ) : null}
                </td>
                <td>{item.vendor_code}</td>
                <td>{item.quantity}</td>
                <td>${item.total_cost}</td>
                <td>
                  {item.requested_delivery_start}
                  <br />
                  {item.requested_delivery_end}
                </td>
                <td>{item.live_status}</td>
                <td className="font-semibold">{item.review_status}</td>
                <td>
                  {readOnly ? (
                    "Read only"
                  ) : item.review_status === "released" ? (
                    <div className="min-w-56 space-y-1">
                      <span className="block text-xs font-semibold uppercase text-slate-500">
                        Purchasing request
                      </span>
                      {item.purchasing_requests.map((request) => (
                        <div key={request.purchase_request_id}>
                          <strong className="block">
                            {request.order_number}
                          </strong>
                          <span className="text-xs text-slate-600">
                            {request.status.replaceAll("_", " ")}
                          </span>
                        </div>
                      ))}
                      {!item.purchasing_requests.length ? "Locked" : null}
                    </div>
                  ) : (
                    <div className="grid min-w-64 gap-1">
                      <div className="flex gap-1">
                        <button
                          className="rounded bg-green-700 px-2 py-1 text-white"
                          disabled={busy}
                          onClick={() => void decide(item.order_id, "approve")}
                        >
                          Approve
                        </button>
                        <button
                          className="rounded bg-red-700 px-2 py-1 text-white"
                          disabled={busy}
                          onClick={() => void decide(item.order_id, "reject")}
                        >
                          Reject
                        </button>
                        <button
                          className="rounded bg-amber-700 px-2 py-1 text-white"
                          disabled={busy}
                          onClick={() => void decide(item.order_id, "revise")}
                        >
                          Revise
                        </button>
                      </div>
                      <input
                        className="rounded border p-1"
                        min="1"
                        onChange={(event) =>
                          setQuantities((current) => ({
                            ...current,
                            [item.order_id]: Number(event.target.value),
                          }))
                        }
                        placeholder={`Revised qty (${item.quantity})`}
                        type="number"
                      />
                      {item.variant_lines.length > 1 ? (
                        <small className="text-amber-700">
                          Aggregate revisions are distributed proportionally
                          across these model lines.
                        </small>
                      ) : null}
                      <input
                        className="rounded border p-1"
                        onChange={(event) =>
                          setReasons((current) => ({
                            ...current,
                            [item.order_id]: event.target.value,
                          }))
                        }
                        placeholder="Reason for reject/revise"
                      />
                    </div>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
