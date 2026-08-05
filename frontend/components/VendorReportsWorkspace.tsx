"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { getVendorReport, VendorReport } from "@/lib/vendor-report-api";

const monthName = (month: number) =>
  new Intl.DateTimeFormat("en-US", { month: "short" }).format(
    new Date(2026, month - 1, 1),
  );
const money = (value: string, currency: string) =>
  new Intl.NumberFormat("en-US", { style: "currency", currency }).format(
    Number(value),
  );

export function VendorReportsWorkspace() {
  const [report, setReport] = useState<VendorReport | null>(null);
  const [year, setYear] = useState<number | undefined>();
  const [error, setError] = useState<string | null>(null);
  const load = useCallback(async () => {
    try {
      const next = await getVendorReport(year);
      setReport(next);
      setYear(next.selected_year);
      setError(null);
    } catch (caught) {
      setError(
        caught instanceof Error ? caught.message : "Unable to load reports.",
      );
    }
  }, [year]);
  useEffect(() => {
    void load();
  }, [load]);
  return (
    <main className="mx-auto max-w-7xl p-4 sm:p-8">
      <Link className="text-sm text-slate-600" href="/">
        ← Command center
      </Link>
      <div className="mt-4 flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="brand-eyebrow">Vendor intelligence</p>
          <h1 className="mt-2 text-3xl font-bold">Reports</h1>
          <p className="mt-2 text-slate-600">
            Monthly and annual purchasing performance for your vendor identity.
          </p>
        </div>
        {report ? (
          <label className="font-bold">
            Reporting year
            <select
              className="ml-3 rounded-xl border p-3"
              onChange={(event) => setYear(Number(event.target.value))}
              value={report.selected_year}
            >
              {report.available_years.map((item) => (
                <option key={item}>{item}</option>
              ))}
            </select>
          </label>
        ) : null}
      </div>
      {error ? (
        <p className="mt-4 rounded-xl bg-red-50 p-3 text-red-800">{error}</p>
      ) : null}
      {report ? (
        <>
          <section className="mt-6 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            {[
              ["Purchase orders", report.purchase_order_count],
              ["Active POs", report.active_po_count],
              ["Needs attention", report.attention_po_count],
              ["Unreconciled invoices", report.unreconciled_invoice_count],
              ["Units ordered", Number(report.units_ordered).toLocaleString()],
              [
                "Units received",
                Number(report.units_received).toLocaleString(),
              ],
              [
                "Fill rate",
                report.fill_rate
                  ? `${Number(report.fill_rate).toFixed(1)}%`
                  : "—",
              ],
              ["Rejected / cancelled", report.rejected_or_cancelled_count],
            ].map(([label, value]) => (
              <article className="rounded-2xl bg-white p-5" key={label}>
                <p className="text-xs font-bold uppercase text-slate-500">
                  {label}
                </p>
                <strong className="mt-2 block text-2xl text-blue-950">
                  {value}
                </strong>
              </article>
            ))}
          </section>
          <section className="mt-5 grid gap-4 lg:grid-cols-2">
            <article className="rounded-2xl bg-white p-5">
              <h2 className="text-xl font-bold">Annual spend</h2>
              {report.annual_spend.map((item) => (
                <p
                  className="mt-3 flex justify-between text-lg"
                  key={item.currency}
                >
                  <span>{item.currency}</span>
                  <strong>{money(item.amount, item.currency)}</strong>
                </p>
              ))}
              {!report.annual_spend.length ? (
                <p className="mt-3 text-slate-500">No spend in this year.</p>
              ) : null}
            </article>
            <article className="rounded-2xl bg-white p-5">
              <h2 className="text-xl font-bold">Average PO value</h2>
              {report.average_po_value.map((item) => (
                <p
                  className="mt-3 flex justify-between text-lg"
                  key={item.currency}
                >
                  <span>{item.currency}</span>
                  <strong>{money(item.amount, item.currency)}</strong>
                </p>
              ))}
            </article>
          </section>
          <section className="mt-5 rounded-2xl bg-white p-5">
            <h2 className="text-xl font-bold">Monthly spend</h2>
            <div className="mt-4 overflow-x-auto">
              <table className="w-full min-w-[700px] text-left text-sm">
                <thead>
                  <tr className="border-b">
                    <th className="py-2">Month</th>
                    <th>Currency</th>
                    <th>POs</th>
                    <th>Ordered</th>
                    <th>Received</th>
                    <th>Spend</th>
                  </tr>
                </thead>
                <tbody>
                  {report.monthly_spend.map((item) => (
                    <tr
                      className="border-b"
                      key={`${item.month}-${item.currency}`}
                    >
                      <td className="py-3 font-bold">
                        {monthName(item.month)}
                      </td>
                      <td>{item.currency}</td>
                      <td>{item.purchase_order_count}</td>
                      <td>{item.quantity}</td>
                      <td>{item.received_quantity}</td>
                      <td className="font-bold">
                        {money(item.spend, item.currency)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
          <section className="mt-5 rounded-2xl bg-white p-5">
            <h2 className="text-xl font-bold">
              Spend by Department and Product Code
            </h2>
            <div className="mt-4 overflow-x-auto">
              <table className="w-full min-w-[760px] text-left text-sm">
                <thead>
                  <tr className="border-b">
                    <th className="py-2">Department</th>
                    <th>Product Code</th>
                    <th>Currency</th>
                    <th>POs</th>
                    <th>Units</th>
                    <th>Spend</th>
                  </tr>
                </thead>
                <tbody>
                  {report.category_spend.map((item) => (
                    <tr
                      className="border-b"
                      key={`${item.department}-${item.product_code}-${item.currency}`}
                    >
                      <td className="py-3 font-bold">{item.department}</td>
                      <td>{item.product_code}</td>
                      <td>{item.currency}</td>
                      <td>{item.purchase_order_count}</td>
                      <td>{item.quantity}</td>
                      <td className="font-bold">
                        {money(item.spend, item.currency)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        </>
      ) : null}
    </main>
  );
}
