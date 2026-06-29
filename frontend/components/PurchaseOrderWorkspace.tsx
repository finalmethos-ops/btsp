"use client";

import Link from "next/link";
import { FormEvent, useCallback, useEffect, useState } from "react";
import {
  PurchaseOrder,
  PurchaseOrderArtifact,
  PurchaseOrderTransmission,
  createPurchaseOrderTransmission,
  downloadPurchaseOrderArtifact,
  generatePurchaseOrderArtifact,
  getPurchaseOrder,
  listPurchaseOrderArtifacts,
  listPurchaseOrderTransmissions,
  listPurchaseOrders,
  runPurchaseOrderTransmissionAction,
} from "@/lib/purchase-order-api";
import { advanceWorkflow, getPurchaseRequest } from "@/lib/purchasing-api";

const money = (value: string, currency = "USD") =>
  new Intl.NumberFormat("en-US", { style: "currency", currency }).format(
    Number(value),
  );

export function PurchaseOrderWorkspace() {
  const [orders, setOrders] = useState<PurchaseOrder[]>([]);
  const [selected, setSelected] = useState<PurchaseOrder | null>(null);
  const [artifacts, setArtifacts] = useState<PurchaseOrderArtifact[]>([]);
  const [transmissions, setTransmissions] = useState<
    PurchaseOrderTransmission[]
  >([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const run = useCallback(async (operation: () => Promise<void>) => {
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
  }, []);

  const loadList = useCallback(
    async () => setOrders(await listPurchaseOrders()),
    [],
  );
  const refresh = useCallback(
    async (id: string) => {
      const [order, files, handoffs] = await Promise.all([
        getPurchaseOrder(id),
        listPurchaseOrderArtifacts(id),
        listPurchaseOrderTransmissions(id),
      ]);
      setSelected(order);
      setArtifacts(files);
      setTransmissions(handoffs);
      await loadList();
    },
    [loadList],
  );

  useEffect(() => {
    void run(loadList);
  }, [loadList, run]);

  async function advanceSources() {
    if (!selected) return;
    for (const source of selected.sources) {
      const request = await getPurchaseRequest(source.purchase_request_id);
      if (request.status === "po_created" && request.workflow_instance_id) {
        await advanceWorkflow(request.workflow_instance_id, "generate_po");
      }
    }
    setNotice(
      "Source workflows are ready for internal transmission preparation.",
    );
  }

  async function download(artifact: PurchaseOrderArtifact) {
    if (!selected) return;
    const blob = await downloadPurchaseOrderArtifact(selected.id, artifact.id);
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `${selected.po_number}.${artifact.artifact_format}`;
    anchor.click();
    URL.revokeObjectURL(url);
  }

  if (!selected) {
    return (
      <main className="mx-auto max-w-6xl p-8">
        <Link className="text-sm text-slate-600" href="/">
          ← Dashboard
        </Link>
        <h1 className="mt-4 text-3xl font-bold">Purchase Orders</h1>
        <p className="mt-2 text-slate-600">
          Generated BPP and Independent purchasing artifacts.
        </p>
        {error && (
          <p className="mt-4 rounded bg-red-50 p-3 text-red-700">{error}</p>
        )}
        <section className="mt-6 overflow-hidden rounded-lg bg-white shadow">
          {orders.length === 0 ? (
            <p className="p-5 text-slate-500">
              No Purchase Orders are available in your scope.
            </p>
          ) : (
            orders.map((order) => (
              <button
                className="flex w-full items-center justify-between border-b p-4 text-left hover:bg-slate-50"
                key={order.id}
                onClick={() => void run(() => refresh(order.id))}
              >
                <span>
                  <strong>{order.po_number}</strong>
                  <small className="ml-3 text-slate-500">
                    {order.vendor_code}
                  </small>
                  <small className="ml-3 rounded bg-slate-100 px-2 py-1">
                    {order.status}
                  </small>
                </span>
                <span>{money(order.total, order.currency)}</span>
              </button>
            ))
          )}
        </section>
      </main>
    );
  }

  return (
    <main className="mx-auto max-w-7xl p-8">
      <button
        className="text-sm text-slate-600"
        onClick={() => setSelected(null)}
      >
        ← All Purchase Orders
      </button>
      <header className="mt-4 flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold">{selected.po_number}</h1>
          <p className="mt-1 text-slate-600">
            {selected.vendor_code} · {selected.workflow_code}
          </p>
        </div>
        <div className="text-right">
          <span className="rounded-full bg-slate-100 px-3 py-1 text-sm">
            {selected.status}
          </span>
          <p className="mt-2 text-2xl font-bold">
            {money(selected.total, selected.currency)}
          </p>
        </div>
      </header>
      {error && (
        <p className="mt-4 rounded bg-red-50 p-3 text-red-700">{error}</p>
      )}
      {notice && (
        <p className="mt-4 rounded bg-green-50 p-3 text-green-700">{notice}</p>
      )}
      <div className="mt-6 grid gap-6 lg:grid-cols-[2fr_1fr]">
        <section className="space-y-6">
          <div className="rounded-lg bg-white p-5 shadow">
            <h2 className="text-lg font-semibold">Source requests</h2>
            <div className="mt-3 grid gap-2 md:grid-cols-2">
              {selected.sources.map((source) => (
                <div
                  className="rounded border p-3 text-sm"
                  key={`${source.purchase_request_id}-${source.store_number}`}
                >
                  <strong>Store {source.store_number}</strong>
                  <span className="block break-all text-xs text-slate-500">
                    {source.purchase_request_id}
                  </span>
                </div>
              ))}
            </div>
            <button
              className="mt-4 rounded border px-4 py-2 text-sm disabled:opacity-50"
              disabled={busy}
              onClick={() => void run(advanceSources)}
            >
              Confirm PO generated and prepare source workflows
            </button>
          </div>
          <div className="rounded-lg bg-white p-5 shadow">
            <h2 className="text-lg font-semibold">PO lines</h2>
            <div className="mt-3 overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead>
                  <tr className="border-b text-slate-500">
                    <th className="py-2">Store / Product</th>
                    <th>Qty</th>
                    <th>Unit</th>
                    <th>Freight</th>
                    <th>Tax</th>
                    <th>Total</th>
                  </tr>
                </thead>
                <tbody>
                  {selected.lines.map((line) => (
                    <tr className="border-b" key={line.id}>
                      <td className="py-3">
                        <strong>{line.store_number}</strong> ·{" "}
                        {line.product_name}
                        <small className="block text-slate-500">
                          {line.product_code}
                        </small>
                      </td>
                      <td>{line.quantity}</td>
                      <td>{money(line.unit_price, selected.currency)}</td>
                      <td>{money(line.freight_amount, selected.currency)}</td>
                      <td>{money(line.tax_amount, selected.currency)}</td>
                      <td>{money(line.extended_amount, selected.currency)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </section>
        <aside className="space-y-6">
          <div className="rounded-lg bg-white p-5 shadow">
            <h2 className="font-semibold">Exports</h2>
            <div className="mt-3 grid grid-cols-3 gap-2">
              {(["pdf", "csv", "json"] as const).map((format) => (
                <button
                  className="rounded border px-2 py-2 text-sm uppercase"
                  disabled={busy}
                  key={format}
                  onClick={() =>
                    void run(async () => {
                      await generatePurchaseOrderArtifact(selected.id, format);
                      await refresh(selected.id);
                    })
                  }
                >
                  {format}
                </button>
              ))}
            </div>
            <ul className="mt-3 space-y-2 text-sm">
              {artifacts.map((artifact) => (
                <li
                  className="flex items-center justify-between rounded bg-slate-50 p-2"
                  key={artifact.id}
                >
                  <span>
                    {artifact.artifact_format.toUpperCase()} v{artifact.version}
                    <small className="block text-slate-500">
                      {Math.ceil(artifact.size_bytes / 1024)} KB
                    </small>
                  </span>
                  <button
                    className="underline"
                    onClick={() => void run(() => download(artifact))}
                  >
                    Download
                  </button>
                </li>
              ))}
            </ul>
          </div>
          <div className="rounded-lg bg-white p-5 shadow">
            <h2 className="font-semibold">Internal transmission</h2>
            <TransmissionPanel
              artifacts={artifacts}
              busy={busy}
              order={selected}
              refresh={refresh}
              run={run}
              transmissions={transmissions}
            />
          </div>
          <div className="rounded-lg bg-white p-5 text-sm shadow">
            <h2 className="font-semibold">Totals</h2>
            <dl className="mt-3 space-y-2">
              <div className="flex justify-between">
                <dt>Subtotal</dt>
                <dd>{money(selected.subtotal, selected.currency)}</dd>
              </div>
              <div className="flex justify-between">
                <dt>Freight</dt>
                <dd>{money(selected.freight_total, selected.currency)}</dd>
              </div>
              <div className="flex justify-between">
                <dt>Tax</dt>
                <dd>{money(selected.tax_total, selected.currency)}</dd>
              </div>
              <div className="flex justify-between border-t pt-2 font-bold">
                <dt>Total</dt>
                <dd>{money(selected.total, selected.currency)}</dd>
              </div>
            </dl>
          </div>
        </aside>
      </div>
    </main>
  );
}

function TransmissionPanel({
  artifacts,
  busy,
  order,
  refresh,
  run,
  transmissions,
}: {
  artifacts: PurchaseOrderArtifact[];
  busy: boolean;
  order: PurchaseOrder;
  refresh: (id: string) => Promise<void>;
  run: (operation: () => Promise<void>) => Promise<void>;
  transmissions: PurchaseOrderTransmission[];
}) {
  async function create(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    await createPurchaseOrderTransmission(order.id, {
      artifact_id: String(form.get("artifact_id")),
      channel: String(form.get("channel")),
      destination: String(form.get("destination") || ""),
      notes: String(form.get("notes") || ""),
    });
    await refresh(order.id);
  }
  const action = (
    transmission: PurchaseOrderTransmission,
    name: string,
    needsReason = false,
  ) =>
    void run(async () => {
      const reason = needsReason
        ? (window.prompt("Record the reason for this action:") ?? "")
        : undefined;
      if (needsReason && !reason) return;
      await runPurchaseOrderTransmissionAction(
        order.id,
        transmission.id,
        name,
        reason,
      );
      await refresh(order.id);
    });
  return (
    <div className="mt-3">
      {artifacts.length > transmissions.length && (
        <form
          className="space-y-2"
          onSubmit={(event) => void run(() => create(event))}
        >
          <select
            className="w-full rounded border p-2"
            name="artifact_id"
            required
          >
            {artifacts
              .filter(
                (artifact) =>
                  !transmissions.some(
                    (item) => item.artifact_id === artifact.id,
                  ),
              )
              .map((artifact) => (
                <option key={artifact.id} value={artifact.id}>
                  {artifact.artifact_format.toUpperCase()} v{artifact.version}
                </option>
              ))}
          </select>
          <select className="w-full rounded border p-2" name="channel">
            <option value="manual">Manual</option>
            <option value="secure_file">Secure file</option>
            <option value="internal_email">Internal email</option>
          </select>
          <input
            className="w-full rounded border p-2"
            name="destination"
            placeholder="Internal destination label"
          />
          <input
            className="w-full rounded border p-2"
            name="notes"
            placeholder="Audit note"
          />
          <button
            className="w-full rounded bg-slate-900 px-3 py-2 text-white"
            disabled={busy}
          >
            Prepare transmission
          </button>
        </form>
      )}
      <ul className="mt-3 space-y-3 text-sm">
        {transmissions.map((item) => (
          <li className="rounded border p-3" key={item.id}>
            <strong>{item.channel}</strong>
            <span className="ml-2 rounded bg-slate-100 px-2 py-1">
              {item.status}
            </span>
            <small className="mt-2 block text-slate-500">
              {item.events.length} audit events
            </small>
            <div className="mt-2 flex flex-wrap gap-2">
              {item.status === "prepared" && (
                <button
                  className="underline"
                  onClick={() => action(item, "release")}
                >
                  Release
                </button>
              )}
              {item.status === "ready" && (
                <>
                  <button
                    className="underline"
                    onClick={() => action(item, "mark_delivered", true)}
                  >
                    Delivered
                  </button>
                  <button
                    className="text-red-600 underline"
                    onClick={() => action(item, "mark_failed", true)}
                  >
                    Failed
                  </button>
                </>
              )}
              {item.status === "failed" && (
                <button
                  className="underline"
                  onClick={() => action(item, "retry", true)}
                >
                  Retry
                </button>
              )}
              {["prepared", "ready", "failed"].includes(item.status) && (
                <button
                  className="text-red-600 underline"
                  onClick={() => action(item, "cancel", true)}
                >
                  Cancel
                </button>
              )}
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}
