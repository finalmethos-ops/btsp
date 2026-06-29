"use client";

import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { generatePurchaseOrders } from "@/lib/purchase-order-api";
import {
  Attachment,
  CatalogProduct,
  CatalogVendor,
  PurchaseRequest,
  PurchaseValidation,
  WorkflowInstance,
  addPurchaseLine,
  clonePurchaseRequest,
  createPurchaseRequest,
  deleteAttachment,
  deletePurchaseLine,
  downloadAttachment,
  getPurchaseRequest,
  getWorkflowInstance,
  listAttachments,
  listProducts,
  listPurchaseRequests,
  listVendors,
  submitPurchaseRequest,
  uploadAttachment,
  validatePurchaseRequest,
} from "@/lib/purchasing-api";

const money = (value: string) =>
  new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" }).format(
    Number(value),
  );

export function PurchaseRequestWorkspace({
  workflowCode,
  title,
}: {
  workflowCode: string;
  title: string;
}) {
  const [requests, setRequests] = useState<PurchaseRequest[]>([]);
  const [vendors, setVendors] = useState<CatalogVendor[]>([]);
  const [selected, setSelected] = useState<PurchaseRequest | null>(null);
  const [products, setProducts] = useState<CatalogProduct[]>([]);
  const [attachments, setAttachments] = useState<Attachment[]>([]);
  const [validation, setValidation] = useState<PurchaseValidation | null>(null);
  const [workflow, setWorkflow] = useState<WorkflowInstance | null>(null);
  const [storeNumber, setStoreNumber] = useState("");
  const [vendorCode, setVendorCode] = useState("");
  const [productCode, setProductCode] = useState("");
  const [quantity, setQuantity] = useState("1");
  const [freight, setFreight] = useState("0");
  const [tax, setTax] = useState("0");
  const [search, setSearch] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const selectedVendorCode = selected?.vendor_code;

  const run = useCallback(async (operation: () => Promise<void>) => {
    setBusy(true);
    setError(null);
    try {
      await operation();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Operation failed");
    } finally {
      setBusy(false);
    }
  }, []);

  const loadList = useCallback(async () => {
    const all = await listPurchaseRequests();
    setRequests(all.filter((item) => item.workflow_code === workflowCode));
  }, [workflowCode]);

  const refresh = useCallback(
    async (id: string) => {
      const item = await getPurchaseRequest(id);
      setSelected(item);
      const [files, result] = await Promise.all([
        listAttachments(id),
        validatePurchaseRequest(id),
      ]);
      setAttachments(files);
      setValidation(result);
      setWorkflow(
        item.workflow_instance_id ? await getWorkflowInstance(id) : null,
      );
      await loadList();
    },
    [loadList],
  );

  useEffect(() => {
    void run(async () => {
      setVendors(await listVendors());
      await loadList();
    });
  }, [loadList, run]);
  useEffect(() => {
    if (!selectedVendorCode) return;
    void run(async () =>
      setProducts(await listProducts(selectedVendorCode, search)),
    );
  }, [search, selectedVendorCode, run]);

  const selectedProduct = useMemo(
    () => products.find((item) => item.product_code === productCode),
    [productCode, products],
  );

  async function create(event: FormEvent) {
    event.preventDefault();
    await run(async () => {
      const item = await createPurchaseRequest({
        workflow_code: workflowCode,
        store_number: storeNumber,
        vendor_code: vendorCode,
      });
      setStoreNumber("");
      setVendorCode("");
      await refresh(item.id);
    });
  }

  if (!selected)
    return (
      <main className="mx-auto max-w-6xl p-8">
        <Link className="text-sm text-slate-600" href="/">
          ← Dashboard
        </Link>
        <div className="mt-4 flex items-end justify-between">
          <div>
            <h1 className="text-3xl font-bold">{title}</h1>
            <p className="mt-2 text-slate-600">
              Create or recover a purchasing request.
            </p>
          </div>
        </div>
        {error && (
          <p className="mt-4 rounded bg-red-50 p-3 text-red-700">{error}</p>
        )}
        <form
          className="mt-6 grid gap-3 rounded-lg bg-white p-5 shadow md:grid-cols-[1fr_1fr_auto]"
          onSubmit={create}
        >
          <label className="text-sm font-medium">
            Store number
            <input
              className="mt-1 w-full rounded border p-2"
              required
              value={storeNumber}
              onChange={(e) => setStoreNumber(e.target.value)}
            />
          </label>
          <label className="text-sm font-medium">
            Vendor
            <select
              className="mt-1 w-full rounded border p-2"
              required
              value={vendorCode}
              onChange={(e) => setVendorCode(e.target.value)}
            >
              <option value="">Select vendor</option>
              {vendors.map((v) => (
                <option key={v.vendor_code} value={v.vendor_code}>
                  {v.vendor_code} — {v.name}
                </option>
              ))}
            </select>
          </label>
          <button
            className="self-end rounded bg-slate-900 px-5 py-2 text-white disabled:opacity-50"
            disabled={busy}
          >
            New request
          </button>
        </form>
        <section className="mt-6 overflow-hidden rounded-lg bg-white shadow">
          <h2 className="border-b p-4 text-lg font-semibold">Requests</h2>
          {requests.length === 0 ? (
            <p className="p-5 text-slate-500">No requests yet.</p>
          ) : (
            requests.map((item) => (
              <button
                className="flex w-full justify-between border-b p-4 text-left hover:bg-slate-50"
                key={item.id}
                onClick={() => void run(() => refresh(item.id))}
              >
                <span>
                  <strong>{item.store_number}</strong> · {item.vendor_code}
                  <small className="ml-3 text-slate-500">{item.status}</small>
                </span>
                <span>{money(item.total)}</span>
              </button>
            ))
          )}
        </section>
      </main>
    );

  return (
    <main className="mx-auto max-w-7xl p-8">
      <button
        className="text-sm text-slate-600"
        onClick={() => setSelected(null)}
      >
        ← All requests
      </button>
      <header className="mt-4 flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold">Purchase Request</h1>
          <p className="mt-1 font-mono text-xs text-slate-500">{selected.id}</p>
        </div>
        <div className="text-right">
          <span className="rounded-full bg-slate-100 px-3 py-1 text-sm">
            {workflow?.current_state ?? selected.status}
          </span>
          <p className="mt-2 text-2xl font-bold">{money(selected.total)}</p>
        </div>
      </header>
      {error && (
        <p className="mt-4 rounded bg-red-50 p-3 text-red-700">{error}</p>
      )}
      <div className="mt-6 grid gap-6 lg:grid-cols-[2fr_1fr]">
        <section className="space-y-6">
          <div className="rounded-lg bg-white p-5 shadow">
            <h2 className="text-lg font-semibold">Request details</h2>
            <dl className="mt-3 grid grid-cols-2 gap-3 text-sm">
              <div>
                <dt className="text-slate-500">Store</dt>
                <dd>{selected.store_number}</dd>
              </div>
              <div>
                <dt className="text-slate-500">Vendor</dt>
                <dd>{selected.vendor_code}</dd>
              </div>
              <div>
                <dt className="text-slate-500">Expires</dt>
                <dd>
                  {selected.expires_at
                    ? new Date(selected.expires_at).toLocaleDateString()
                    : "—"}
                </dd>
              </div>
              <div>
                <dt className="text-slate-500">Revision</dt>
                <dd>{selected.revision}</dd>
              </div>
            </dl>
          </div>
          <div className="rounded-lg bg-white p-5 shadow">
            <h2 className="text-lg font-semibold">Line items</h2>
            {selected.status === "draft" && (
              <form
                className="mt-4 grid gap-2 md:grid-cols-6"
                onSubmit={(e) => {
                  e.preventDefault();
                  void run(async () => {
                    await addPurchaseLine(selected.id, {
                      product_code: productCode,
                      quantity: Number(quantity),
                      freight_amount: Number(freight),
                      tax_amount: Number(tax),
                    });
                    setProductCode("");
                    await refresh(selected.id);
                  });
                }}
              >
                <input
                  className="rounded border p-2 md:col-span-2"
                  placeholder="Search products"
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                />
                <select
                  className="rounded border p-2 md:col-span-2"
                  required
                  value={productCode}
                  onChange={(e) => setProductCode(e.target.value)}
                >
                  <option value="">Select product</option>
                  {products.map((p) => (
                    <option key={p.product_code} value={p.product_code}>
                      {p.product_code} — {p.name} ({money(p.unit_price)})
                    </option>
                  ))}
                </select>
                <input
                  aria-label="Quantity"
                  className="rounded border p-2"
                  min={selectedProduct?.minimum_order_quantity ?? "0.0001"}
                  required
                  step="0.0001"
                  type="number"
                  value={quantity}
                  onChange={(e) => setQuantity(e.target.value)}
                />
                <button className="rounded bg-slate-900 px-3 text-white">
                  Add
                </button>
                <input
                  aria-label="Freight"
                  className="rounded border p-2"
                  min="0"
                  step="0.01"
                  type="number"
                  value={freight}
                  onChange={(e) => setFreight(e.target.value)}
                />
                <input
                  aria-label="Tax"
                  className="rounded border p-2"
                  min="0"
                  step="0.01"
                  type="number"
                  value={tax}
                  onChange={(e) => setTax(e.target.value)}
                />
              </form>
            )}
            <div className="mt-4 overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead>
                  <tr className="border-b text-slate-500">
                    <th className="py-2">Product</th>
                    <th>Qty</th>
                    <th>Unit</th>
                    <th>Freight</th>
                    <th>Tax</th>
                    <th>Total</th>
                    <th />
                  </tr>
                </thead>
                <tbody>
                  {selected.line_items.map((line) => (
                    <tr className="border-b" key={line.id}>
                      <td className="py-3">
                        {line.product_name}
                        <small className="block text-slate-500">
                          {line.product_code}
                        </small>
                      </td>
                      <td>{line.quantity}</td>
                      <td>{money(line.unit_price)}</td>
                      <td>{money(line.freight_amount)}</td>
                      <td>{money(line.tax_amount)}</td>
                      <td>{money(line.extended_amount)}</td>
                      <td>
                        {selected.status === "draft" && (
                          <button
                            className="text-red-600"
                            onClick={() =>
                              void run(async () => {
                                await deletePurchaseLine(selected.id, line.id);
                                await refresh(selected.id);
                              })
                            }
                          >
                            Remove
                          </button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </section>
        <aside className="space-y-6">
          <div className="rounded-lg bg-white p-5 shadow">
            <h2 className="font-semibold">Readiness</h2>
            {validation?.ready ? (
              <p className="mt-3 text-green-700">Ready to submit</p>
            ) : (
              <ul className="mt-3 list-disc space-y-1 pl-5 text-sm text-amber-700">
                {validation?.errors.map((item) => (
                  <li key={`${item.code}-${item.message}`}>{item.message}</li>
                ))}
              </ul>
            )}
            {selected.status === "draft" && (
              <button
                className="mt-4 w-full rounded bg-emerald-700 px-4 py-2 text-white disabled:opacity-50"
                disabled={!validation?.ready || busy}
                onClick={() =>
                  void run(async () => {
                    await submitPurchaseRequest(selected.id);
                    await refresh(selected.id);
                  })
                }
              >
                Submit request
              </button>
            )}
            <button
              className="mt-2 w-full rounded border px-4 py-2"
              onClick={() =>
                void run(async () => {
                  const copy = await clonePurchaseRequest(selected.id);
                  await refresh(copy.id);
                })
              }
            >
              Clone as draft
            </button>
            {selected.status === "po_created" && (
              <button
                className="mt-2 w-full rounded bg-blue-700 px-4 py-2 text-white"
                onClick={() =>
                  void run(async () => {
                    await generatePurchaseOrders([selected.id]);
                    window.location.href = "/purchase-orders";
                  })
                }
              >
                Generate Purchase Order
              </button>
            )}
          </div>
          <div className="rounded-lg bg-white p-5 shadow">
            <h2 className="font-semibold">Attachments</h2>
            <form
              className="mt-3 space-y-2"
              onSubmit={(e) => {
                e.preventDefault();
                const form = new FormData(e.currentTarget);
                const file = form.get("file");
                if (!(file instanceof File) || !file.size) return;
                void run(async () => {
                  await uploadAttachment(
                    selected.id,
                    String(form.get("category")),
                    file,
                  );
                  await refresh(selected.id);
                  e.currentTarget.reset();
                });
              }}
            >
              <select className="w-full rounded border p-2" name="category">
                <option value="quote">Quote</option>
                <option value="vendor_document">Vendor document</option>
                <option value="image">Image</option>
                <option value="pdf">PDF</option>
                <option value="supporting_document">Supporting document</option>
              </select>
              <input
                className="w-full text-sm"
                name="file"
                required
                type="file"
              />
              <button className="w-full rounded border px-3 py-2">
                Upload
              </button>
            </form>
            <ul className="mt-3 space-y-2 text-sm">
              {attachments.map((file) => (
                <li className="rounded bg-slate-50 p-2" key={file.id}>
                  <button
                    className="text-left font-medium underline"
                    onClick={() =>
                      void run(async () => {
                        const blob = await downloadAttachment(
                          selected.id,
                          file.id,
                        );
                        const url = URL.createObjectURL(blob);
                        const anchor = document.createElement("a");
                        anchor.href = url;
                        anchor.download = file.original_filename;
                        anchor.click();
                        URL.revokeObjectURL(url);
                      })
                    }
                  >
                    {file.original_filename}
                  </button>
                  <span className="block text-xs text-slate-500">
                    {file.category} · {Math.ceil(file.size_bytes / 1024)} KB
                  </span>
                  {selected.status === "draft" && (
                    <button
                      className="mt-1 text-xs text-red-600"
                      onClick={() =>
                        void run(async () => {
                          await deleteAttachment(selected.id, file.id);
                          await refresh(selected.id);
                        })
                      }
                    >
                      Delete
                    </button>
                  )}
                </li>
              ))}
            </ul>
          </div>
          <div className="rounded-lg bg-white p-5 shadow">
            <h2 className="font-semibold">Workflow timeline</h2>
            <div className="mt-3 border-l-2 border-slate-200 pl-4">
              <p className="font-medium">
                {workflow?.current_state ?? "Draft"}
              </p>
              <p className="text-xs text-slate-500">
                {workflow
                  ? `Updated ${new Date(workflow.updated_at).toLocaleString()}`
                  : "Workflow begins on submission"}
              </p>
            </div>
          </div>
        </aside>
      </div>
    </main>
  );
}
