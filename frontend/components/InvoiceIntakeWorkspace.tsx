"use client";

import Link from "next/link";
import { FormEvent, useCallback, useEffect, useState } from "react";
import {
  downloadInvoiceIntakePDF,
  InvoiceIntakeDocument,
  listInvoiceIntake,
  uploadInvoicePDFs,
} from "@/lib/invoice-intake-api";

export function InvoiceIntakeWorkspace() {
  const [documents, setDocuments] = useState<InvoiceIntakeDocument[]>([]);
  const [files, setFiles] = useState<File[]>([]);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const load = useCallback(
    async () => setDocuments(await listInvoiceIntake()),
    [],
  );
  useEffect(() => {
    void load().catch((caught: unknown) =>
      setError(
        caught instanceof Error
          ? caught.message
          : "Unable to load invoice intake.",
      ),
    );
  }, [load]);
  async function upload(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!files.length) return;
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      const result = await uploadInvoicePDFs(files);
      setMessage(
        `${result.uploaded_files} PDF file(s) processed into ${result.separated_invoices} unique invoice(s)${result.duplicate_invoices ? `; ${result.duplicate_invoices} duplicate(s) skipped` : ""}.`,
      );
      setFiles([]);
      event.currentTarget.reset();
      await load();
    } catch (caught) {
      setError(
        caught instanceof Error
          ? caught.message
          : "Unable to process the invoice PDFs.",
      );
    } finally {
      setBusy(false);
    }
  }
  async function viewPDF(document: InvoiceIntakeDocument) {
    const blob = await downloadInvoiceIntakePDF(document.id);
    const url = URL.createObjectURL(blob);
    window.open(url, "_blank", "noopener,noreferrer");
    window.setTimeout(() => URL.revokeObjectURL(url), 60_000);
  }
  return (
    <main className="mx-auto max-w-7xl p-4 sm:p-8">
      <Link className="text-sm text-slate-600" href="/">
        ← Command center
      </Link>
      <p className="brand-eyebrow mt-4">Vendor & Reconciliation</p>
      <h1 className="mt-2 text-3xl font-bold">Submit invoices</h1>
      <p className="mt-2 text-slate-600">
        Upload one or several PDF files. Multi-invoice PDFs are separated into
        unique stored invoices and analyzed for vendor, store, invoice number,
        and PO hints.
      </p>
      {message ? (
        <p className="mt-4 rounded-xl bg-green-50 p-3 text-green-800">
          {message}
        </p>
      ) : null}
      {error ? (
        <p className="mt-4 rounded-xl bg-red-50 p-3 text-red-800">{error}</p>
      ) : null}
      <form className="mt-5 rounded-2xl bg-white p-5" onSubmit={upload}>
        <label className="block font-bold">
          Invoice PDF files
          <input
            accept="application/pdf,.pdf"
            className="mt-2 block w-full rounded-xl border p-3 font-normal"
            multiple
            onChange={(event) => setFiles(Array.from(event.target.files ?? []))}
            required
            type="file"
          />
        </label>
        <p className="mt-2 text-sm text-slate-500">
          Up to 25 PDFs per batch, 20 MB each. Selected: {files.length}
        </p>
        <button
          className="mt-4 rounded-xl bg-blue-900 px-5 py-3 font-bold text-white disabled:opacity-50"
          disabled={busy || !files.length}
        >
          {busy ? "Reading and separating invoices…" : "Upload invoices"}
        </button>
      </form>

      <section className="mt-6">
        <div className="flex items-end justify-between gap-3">
          <div>
            <p className="brand-eyebrow">Shared intake queue</p>
            <h2 className="text-2xl font-bold">Unreconciled invoices</h2>
          </div>
          <span className="rounded-full bg-yellow-400 px-3 py-1 font-bold text-slate-950">
            {documents.length}
          </span>
        </div>
        <div className="mt-4 grid gap-4 lg:grid-cols-2">
          {documents.map((document) => (
            <article
              className="rounded-2xl border bg-white p-5"
              key={document.id}
            >
              <div className="flex items-start justify-between gap-3">
                <div>
                  <p className="text-xs font-bold uppercase text-slate-500">
                    Invoice
                  </p>
                  <h3 className="text-lg font-bold">
                    {document.invoice_number ?? "Number not detected"}
                  </h3>
                  <p className="text-xs text-slate-500">
                    {document.original_filename} · page {document.page_start}
                    {document.page_end !== document.page_start
                      ? `–${document.page_end}`
                      : ""}
                  </p>
                </div>
                <span className="rounded-full bg-amber-100 px-3 py-1 text-xs font-bold text-amber-900">
                  Unreconciled
                </span>
              </div>
              <dl className="mt-4 grid grid-cols-2 gap-3 rounded-xl bg-slate-50 p-4 text-sm">
                <div>
                  <dt className="text-slate-500">Vendor detected</dt>
                  <dd className="font-bold">
                    {document.detected_vendor_code ?? "Needs review"}
                  </dd>
                </div>
                <div>
                  <dt className="text-slate-500">Store detected</dt>
                  <dd className="font-bold">
                    {document.detected_store_number ?? "Needs review"}
                  </dd>
                </div>
                <div>
                  <dt className="text-slate-500">PO detected</dt>
                  <dd className="font-bold">
                    {document.detected_po_number ?? "Not found"}
                  </dd>
                </div>
                <div>
                  <dt className="text-slate-500">Suggested pairing</dt>
                  <dd className="font-bold text-blue-900">
                    {document.suggested_po_number ?? "No confident match"}
                  </dd>
                </div>
              </dl>
              <button
                className="mt-4 rounded-lg border px-4 py-2 font-bold"
                onClick={() => void viewPDF(document)}
                type="button"
              >
                View stored PDF
              </button>
            </article>
          ))}
          {!documents.length ? (
            <p className="rounded-2xl bg-white p-8 text-center text-slate-500">
              No unreconciled invoice PDFs are waiting.
            </p>
          ) : null}
        </div>
      </section>
    </main>
  );
}
