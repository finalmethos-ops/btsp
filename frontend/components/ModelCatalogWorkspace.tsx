"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import {
  getModelCatalogCostHistory,
  searchModelCatalog,
} from "@/lib/model-catalog-api";
import {
  listModelCategories,
  ModelCategory,
  VendorModel,
  VendorModelClassification,
  VendorModelCost,
} from "@/lib/vendor-model-api";
import { CatalogVendor, listVendors } from "@/lib/purchasing-api";

const money = (value: string, currency: string) =>
  new Intl.NumberFormat("en-US", {
    style: "currency",
    currency,
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(Number(value));

export function ModelCatalogWorkspace() {
  const [models, setModels] = useState<VendorModel[]>([]);
  const [selected, setSelected] = useState<VendorModel | null>(null);
  const [history, setHistory] = useState<VendorModelCost[]>([]);
  const [search, setSearch] = useState("");
  const [vendor, setVendor] = useState("");
  const [department, setDepartment] = useState("");
  const [productCategoryCode, setProductCategoryCode] = useState("");
  const [classification, setClassification] =
    useState<VendorModelClassification>("all");
  const [categories, setCategories] = useState<ModelCategory[]>([]);
  const [vendors, setVendors] = useState<CatalogVendor[]>([]);
  const [error, setError] = useState<string | null>(null);
  const load = useCallback(async () => {
    try {
      const next = await searchModelCatalog(
        search,
        vendor,
        department,
        productCategoryCode,
        classification,
      );
      setModels(next);
      setSelected(
        (current) =>
          next.find((item) => item.product_code === current?.product_code) ??
          next[0] ??
          null,
      );
      setError(null);
    } catch (caught) {
      setError(
        caught instanceof Error
          ? caught.message
          : "Unable to load the model catalog.",
      );
    }
  }, [classification, department, productCategoryCode, search, vendor]);
  useEffect(() => {
    void Promise.all([listModelCategories(), listVendors(false)]).then(
      ([nextCategories, nextVendors]) => {
        setCategories(nextCategories);
        setVendors(nextVendors);
      },
    );
  }, []);
  useEffect(() => {
    const timer = window.setTimeout(() => void load(), 250);
    return () => window.clearTimeout(timer);
  }, [load]);
  useEffect(() => {
    if (selected)
      void getModelCatalogCostHistory(selected.product_code).then(setHistory);
    else setHistory([]);
  }, [selected]);
  return (
    <main className="mx-auto max-w-7xl p-4 sm:p-8">
      <Link className="text-sm text-slate-600" href="/">
        ← Command center
      </Link>
      <p className="brand-eyebrow mt-4">Read-only reference</p>
      <h1 className="mt-2 text-3xl font-bold">Model Catalog</h1>
      <p className="mt-2 text-slate-600">
        Search model specifications and historical costs for purchase and
        invoice validation. Changes are disabled.
      </p>
      {error ? (
        <p className="mt-4 rounded-xl bg-red-50 p-3 text-red-800">{error}</p>
      ) : null}
      <div className="mt-6 grid min-w-0 gap-5 lg:grid-cols-[minmax(0,360px)_minmax(0,1fr)]">
        <section className="min-w-0 overflow-hidden rounded-2xl bg-white p-4">
          <div className="grid gap-2">
            <input
              className="w-full min-w-0 max-w-full rounded-xl border p-3"
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search code, name, brand, category"
              value={search}
            />
            <select
              className="w-full min-w-0 max-w-full rounded-xl border p-3"
              onChange={(e) => setVendor(e.target.value)}
              value={vendor}
            >
              <option value="">All vendors</option>
              {vendors.map((item) => (
                <option key={item.vendor_code} value={item.vendor_code}>
                  {item.name} · {item.vendor_code}
                </option>
              ))}
            </select>
            <fieldset className="mt-2">
              <legend className="text-sm font-semibold">Model type</legend>
              <div className="mt-2 grid grid-cols-2 gap-2">
                {(
                  [
                    ["all", "All"],
                    ["clump", "Clumps"],
                    ["part_of_clump", "Part of clump"],
                    ["single_item", "Single items"],
                  ] as Array<[VendorModelClassification, string]>
                ).map(([value, label]) => (
                  <button
                    className={`rounded-lg border px-3 py-2 text-sm font-semibold ${classification === value ? "selected-object" : "bg-white"}`}
                    key={value}
                    onClick={() => setClassification(value)}
                    type="button"
                  >
                    {label}
                  </button>
                ))}
              </div>
            </fieldset>
            <select
              className="w-full min-w-0 max-w-full rounded-xl border p-3"
              onChange={(event) => {
                setDepartment(event.target.value);
                setProductCategoryCode("");
              }}
              value={department}
            >
              <option value="">All departments</option>
              {[...new Set(categories.map((item) => item.department))].map(
                (item) => (
                  <option key={item} value={item}>
                    {item}
                  </option>
                ),
              )}
            </select>
            <select
              className="w-full min-w-0 max-w-full rounded-xl border p-3"
              disabled={!department}
              onChange={(event) => setProductCategoryCode(event.target.value)}
              value={productCategoryCode}
            >
              <option value="">All product codes</option>
              {categories
                .filter((item) => item.department === department)
                .map((item) => (
                  <option key={item.id} value={item.product_category_code}>
                    {item.product_category_code}
                  </option>
                ))}
            </select>
          </div>
          <p className="my-3 text-xs font-semibold uppercase text-slate-500">
            {models.length} models
          </p>
          <div className="max-h-[65vh] space-y-2 overflow-y-auto">
            {models.map((model) => (
              <button
                className={`w-full rounded-xl border p-3 text-left ${selected?.product_code === model.product_code ? "selected-object" : ""}`}
                key={model.product_code}
                onClick={() => setSelected(model)}
              >
                <strong className="block">{model.model_identifier}</strong>
                <span
                  className={`block truncate text-sm ${
                    selected?.product_code === model.product_code
                      ? "font-semibold !text-slate-950"
                      : "text-slate-600"
                  }`}
                >
                  {model.name}
                </span>
                <span
                  className={`text-xs ${
                    selected?.product_code === model.product_code
                      ? "font-semibold !text-slate-950"
                      : "text-slate-500"
                  }`}
                >
                  {model.vendor_code} · {model.department ?? "Unassigned"} ·{" "}
                  {model.product_category_code ?? "Unassigned"}
                </span>
              </button>
            ))}
          </div>
        </section>
        {selected ? (
          <div className="space-y-5">
            <section className="rounded-2xl bg-white p-6">
              <div className="flex justify-between gap-3">
                <div>
                  <p className="brand-eyebrow">{selected.vendor_code}</p>
                  <h2 className="text-2xl font-bold">{selected.name}</h2>
                  <p className="text-slate-500">
                    Model {selected.model_identifier}
                  </p>
                </div>
                <strong className="text-xl">
                  {money(selected.unit_price, selected.currency)}
                </strong>
              </div>
              <dl className="mt-6 grid gap-4 sm:grid-cols-3">
                <div>
                  <dt className="text-xs text-slate-500">Brand</dt>
                  <dd>{selected.brand ?? "—"}</dd>
                </div>
                <div>
                  <dt className="text-xs text-slate-500">Department</dt>
                  <dd>{selected.department ?? "—"}</dd>
                </div>
                <div>
                  <dt className="text-xs text-slate-500">Product Code</dt>
                  <dd>{selected.product_category_code ?? "—"}</dd>
                </div>
                <div>
                  <dt className="text-xs text-slate-500">Status</dt>
                  <dd>
                    {selected.is_active && selected.is_available
                      ? "Available"
                      : "Unavailable"}
                  </dd>
                </div>
              </dl>
            </section>
            <section className="rounded-2xl bg-white p-6">
              <h2 className="text-xl font-bold">Cost history</h2>
              <div className="mt-4 overflow-x-auto">
                <table className="w-full min-w-[600px] text-left text-sm">
                  <thead>
                    <tr className="border-b">
                      <th className="py-2">Cost</th>
                      <th>Effective from</th>
                      <th>Effective to</th>
                      <th>Source</th>
                    </tr>
                  </thead>
                  <tbody>
                    {history.map((item) => (
                      <tr className="border-b" key={item.id}>
                        <td className="py-3 font-semibold">
                          {money(item.unit_price, item.currency)}
                        </td>
                        <td>
                          {new Date(item.effective_from).toLocaleString()}
                        </td>
                        <td>
                          {item.effective_to
                            ? new Date(item.effective_to).toLocaleString()
                            : "Current"}
                        </td>
                        <td>{item.source.replaceAll("-", " ")}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>
          </div>
        ) : null}
      </div>
    </main>
  );
}
