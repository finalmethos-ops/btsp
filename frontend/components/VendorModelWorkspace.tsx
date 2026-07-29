"use client";

import Link from "next/link";
import { FormEvent, useCallback, useEffect, useState } from "react";
import { useAuth } from "@/lib/auth";
import {
  exportVendorModels,
  getVendorModelCostHistory,
  importVendorModels,
  listModelCategories,
  listVendorModels,
  listVendorMOQRules,
  updateVendorModel,
  VendorModel,
  VendorModelClassification,
  VendorModelCost,
  ModelCategory,
  VendorMOQRule,
} from "@/lib/vendor-model-api";

const money = (value: string, currency: string) =>
  new Intl.NumberFormat("en-US", {
    style: "currency",
    currency,
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(Number(value));

export function VendorModelWorkspace() {
  const { user } = useAuth();
  const [models, setModels] = useState<VendorModel[]>([]);
  const [selected, setSelected] = useState<VendorModel | null>(null);
  const [history, setHistory] = useState<VendorModelCost[]>([]);
  const [moqRules, setMoqRules] = useState<VendorMOQRule[]>([]);
  const [modelCategories, setModelCategories] = useState<ModelCategory[]>([]);
  const [department, setDepartment] = useState("");
  const [productCategoryCode, setProductCategoryCode] = useState("");
  const [search, setSearch] = useState("");
  const [classification, setClassification] =
    useState<VendorModelClassification>("all");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const activeMOQRules = moqRules.filter((rule) => rule.is_active);

  const load = useCallback(
    async (term = "", filter: VendorModelClassification = "all") => {
      const [next, rules, categories] = await Promise.all([
        listVendorModels(term, filter),
        listVendorMOQRules(),
        listModelCategories(),
      ]);
      setMoqRules(rules);
      setModels(next);
      setModelCategories(categories);
      setSelected((current) =>
        current
          ? (next.find((item) => item.product_code === current.product_code) ??
            next[0] ??
            null)
          : (next[0] ?? null),
      );
    },
    [],
  );

  useEffect(() => {
    void load().catch((caught: unknown) =>
      setError(
        caught instanceof Error ? caught.message : "Unable to load models",
      ),
    );
  }, [load]);

  useEffect(() => {
    if (!selected) {
      setHistory([]);
      return;
    }
    void getVendorModelCostHistory(selected.product_code)
      .then(setHistory)
      .catch(() => setHistory([]));
  }, [selected]);
  useEffect(() => {
    setDepartment(selected?.department ?? "");
    setProductCategoryCode(selected?.product_category_code ?? "");
  }, [selected]);

  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selected) return;
    const data = new FormData(event.currentTarget);
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      const previousProductCode = selected.product_code;
      const updated = await updateVendorModel(selected.product_code, {
        model_number: String(data.get("model_number") ?? "").trim(),
        name: String(data.get("name") ?? "").trim(),
        department: String(data.get("department") ?? "").trim(),
        product_category_code: String(
          data.get("product_category_code") ?? "",
        ).trim(),
        brand: String(data.get("brand") ?? "").trim() || null,
        is_clump: data.get("is_clump") === "on",
        part_of_clump: data.get("part_of_clump") === "on",
        cost_effective_start_date:
          String(data.get("cost_effective_start_date") ?? "").trim() || null,
        cost_status: String(data.get("cost_status") ?? "Approved").trim(),
        unit_price: Number(data.get("unit_price")),
        currency: String(data.get("currency") ?? "USD").toUpperCase(),
        moq_rule_id: data.get("moq_rule_id")
          ? Number(data.get("moq_rule_id"))
          : null,
        is_available: data.get("is_available") === "on",
        is_active: data.get("is_active") === "on",
      });
      setModels((current) =>
        current.map((model) =>
          model.product_code === previousProductCode ? updated : model,
        ),
      );
      setSelected(updated);
      await load(search, classification);
      setSelected(updated);
      setMessage(
        `${updated.model_identifier} saved. Existing purchase prices were not changed.`,
      );
    } catch (caught) {
      setError(
        caught instanceof Error ? caught.message : "Model could not be saved",
      );
    } finally {
      setBusy(false);
    }
  }

  async function importFile(file: File | undefined) {
    if (!file) return;
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      const result = await importVendorModels(file);
      await load(search, classification);
      setMessage(
        `Import complete: ${result.created} new, ${result.updated} changed, ${result.unchanged} unchanged.`,
      );
    } catch (caught) {
      setError(
        caught instanceof Error ? caught.message : "Model import failed",
      );
    } finally {
      setBusy(false);
    }
  }

  async function exportFile() {
    setBusy(true);
    setError(null);
    try {
      await exportVendorModels();
    } catch (caught) {
      setError(
        caught instanceof Error ? caught.message : "Model export failed",
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="mx-auto max-w-7xl p-4 sm:p-8">
      <header className="mb-7 flex flex-col justify-between gap-4 lg:flex-row lg:items-end">
        <div>
          <Link className="text-sm text-slate-600" href="/">
            ← Command center
          </Link>
          <p className="brand-eyebrow mt-4">Vendor catalog</p>
          <h1 className="mt-2 text-3xl font-bold">Model Management</h1>
          <p className="mt-2 max-w-3xl text-slate-600">
            Maintain models for {user?.vendor_code}. Export the current catalog,
            edit it in Excel, and import only new or changed records. Imports
            accept both BTSP workbooks and vendor product exports with landed
            cost, stock, cost status, effective date, and clump fields.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <button
            className="rounded-xl border border-blue-200 bg-white px-4 py-2 font-semibold text-blue-800"
            disabled={busy}
            onClick={() => void exportFile()}
            type="button"
          >
            Export Excel
          </button>
          <label className="cursor-pointer rounded-xl bg-blue-800 px-4 py-2 font-semibold text-white">
            Import Excel
            <input
              accept=".xlsx"
              className="sr-only"
              disabled={busy}
              onChange={(event) => void importFile(event.target.files?.[0])}
              type="file"
            />
          </label>
        </div>
      </header>

      {message ? (
        <p className="mb-4 rounded-xl bg-green-50 p-3 text-sm text-green-800">
          {message}
        </p>
      ) : null}
      {error ? (
        <p className="mb-4 rounded-xl bg-red-50 p-3 text-sm text-red-800">
          {error}
        </p>
      ) : null}

      <div className="grid gap-5 lg:grid-cols-[340px_1fr]">
        <section className="rounded-2xl bg-white p-4">
          <label className="block text-sm font-semibold">
            Search your models
            <input
              className="mt-2 w-full rounded-xl border px-3 py-2"
              onChange={(event) => {
                const value = event.target.value;
                setSearch(value);
                void load(value, classification);
              }}
              placeholder="Code, name, or model number"
              value={search}
            />
          </label>
          <fieldset className="mt-4">
            <legend className="text-sm font-semibold">Model type</legend>
            <div className="mt-2 grid grid-cols-2 gap-2">
              {(
                [
                  ["all", "All"],
                  ["clump", "Clumps"],
                  ["part_of_clump", "Part of Clump"],
                  ["single_item", "Single Items"],
                ] as Array<[VendorModelClassification, string]>
              ).map(([value, label]) => (
                <button
                  className={`rounded-lg border px-3 py-2 text-sm font-semibold ${classification === value ? "selected-object" : "bg-white"}`}
                  key={value}
                  onClick={() => {
                    setClassification(value);
                    void load(search, value);
                  }}
                  type="button"
                >
                  {label}
                </button>
              ))}
            </div>
          </fieldset>
          <p className="mt-4 text-xs font-semibold uppercase tracking-wide text-slate-500">
            {models.length} models
          </p>
          <div className="mt-2 max-h-[65vh] space-y-2 overflow-y-auto pr-1">
            {models.map((model) => (
              <button
                className={`w-full rounded-xl border p-3 text-left ${
                  selected?.product_code === model.product_code
                    ? "selected-object"
                    : "border-slate-200 bg-white"
                }`}
                key={model.product_code}
                onClick={() => setSelected(model)}
                type="button"
              >
                <strong className="block text-sm">
                  {model.model_identifier}
                </strong>
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
                  className={`mt-1 block text-xs ${
                    selected?.product_code === model.product_code
                      ? "font-semibold !text-slate-950"
                      : "text-slate-500"
                  }`}
                >
                  {money(model.unit_price, model.currency)}
                </span>
                <span className="mt-1 block text-xs text-slate-500">
                  {model.is_available ? "In stock" : "Out of stock"} ·{" "}
                  {model.cost_status}
                </span>
              </button>
            ))}
          </div>
        </section>

        {selected ? (
          <div className="space-y-5">
            <form
              className="rounded-2xl bg-white p-5 sm:p-6"
              key={`${selected.product_code}-${selected.name}`}
              onSubmit={save}
            >
              <div className="mb-5 flex flex-wrap items-center justify-between gap-2">
                <div>
                  <p className="brand-eyebrow">
                    Model {selected.model_identifier}
                  </p>
                  <h2 className="mt-1 text-xl font-bold">{selected.name}</h2>
                  <p className="text-sm text-slate-500">Edit model details</p>
                </div>
                <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold">
                  {selected.is_active ? "Active" : "Inactive"}
                </span>
              </div>
              <div className="grid gap-4 sm:grid-cols-2">
                <label className="text-sm font-semibold sm:col-span-2">
                  Model name
                  <input
                    className="mt-1 w-full rounded-xl border p-3"
                    defaultValue={selected.name}
                    name="name"
                    required
                  />
                </label>
                <label className="text-sm font-semibold">
                  Model number
                  <input
                    className="mt-1 w-full rounded-xl border p-3"
                    defaultValue={
                      selected.model_number ?? selected.model_identifier
                    }
                    maxLength={64}
                    name="model_number"
                    required
                  />
                </label>
                <label className="text-sm font-semibold">
                  Brand
                  <input
                    className="mt-1 w-full rounded-xl border p-3"
                    defaultValue={selected.brand ?? ""}
                    name="brand"
                  />
                </label>
                <label className="text-sm font-semibold">
                  Department
                  <select
                    className="mt-1 w-full rounded-xl border p-3"
                    name="department"
                    onChange={(event) => {
                      const nextDepartment = event.target.value;
                      setDepartment(nextDepartment);
                      setProductCategoryCode((current) =>
                        modelCategories.some(
                          (item) =>
                            item.department === nextDepartment &&
                            item.product_category_code === current,
                        )
                          ? current
                          : "",
                      );
                    }}
                    required
                    value={department}
                  >
                    <option value="">Select department</option>
                    {[
                      ...new Set(
                        modelCategories.map((item) => item.department),
                      ),
                    ].map((item) => (
                      <option key={item} value={item}>
                        {item}
                      </option>
                    ))}
                  </select>
                </label>
                <label className="text-sm font-semibold">
                  Product Code
                  <select
                    className="mt-1 w-full rounded-xl border p-3"
                    name="product_category_code"
                    onChange={(event) =>
                      setProductCategoryCode(event.target.value)
                    }
                    required
                    value={productCategoryCode}
                  >
                    <option value="">Select product code</option>
                    {productCategoryCode &&
                    !modelCategories.some(
                      (item) =>
                        item.department === department &&
                        item.product_category_code === productCategoryCode,
                    ) ? (
                      <option value={productCategoryCode}>
                        {productCategoryCode} (saved)
                      </option>
                    ) : null}
                    {modelCategories
                      .filter((item) => item.department === department)
                      .map((item) => (
                        <option
                          key={item.id}
                          value={item.product_category_code}
                        >
                          {item.product_category_code}
                        </option>
                      ))}
                  </select>
                </label>
                <label className="text-sm font-semibold">
                  MOQ profile
                  {activeMOQRules.length === 0 ? (
                    <div className="mt-1 rounded-xl border bg-slate-50 p-3 font-normal text-slate-600">
                      No MOQ profile configured
                    </div>
                  ) : activeMOQRules.length === 1 ? (
                    <>
                      <input
                        name="moq_rule_id"
                        type="hidden"
                        value={activeMOQRules[0].id}
                      />
                      <div className="mt-1 rounded-xl border border-yellow-400 bg-yellow-100 p-3 font-normal text-slate-950">
                        {activeMOQRules[0].name} ({activeMOQRules[0].code}) —
                        automatically applies to every model
                      </div>
                    </>
                  ) : (
                    <select
                      className="mt-1 w-full rounded-xl border p-3"
                      defaultValue={selected.moq_rule_id ?? ""}
                      name="moq_rule_id"
                      required
                    >
                      <option value="">Select MOQ</option>
                      {activeMOQRules.map((rule) => (
                        <option key={rule.id} value={rule.id}>
                          {rule.name} ({rule.code})
                        </option>
                      ))}
                    </select>
                  )}
                </label>
                <label className="text-sm font-semibold">
                  Landed / Standard Cost
                  <input
                    className="mt-1 w-full rounded-xl border p-3"
                    defaultValue={selected.unit_price}
                    min="0"
                    name="unit_price"
                    required
                    step="0.01"
                    type="number"
                  />
                </label>
                <label className="text-sm font-semibold">
                  Effective start date
                  <input
                    className="mt-1 w-full rounded-xl border p-3"
                    defaultValue={selected.cost_effective_start_date ?? ""}
                    name="cost_effective_start_date"
                    type="date"
                  />
                </label>
                <label className="text-sm font-semibold">
                  Cost status
                  <select
                    className="mt-1 w-full rounded-xl border p-3"
                    defaultValue={selected.cost_status}
                    name="cost_status"
                  >
                    <option value="Approved">Approved</option>
                    <option value="Pending">Pending</option>
                    <option value="Rejected">Rejected</option>
                    <option value="Expired">Expired</option>
                  </select>
                </label>
                <label className="text-sm font-semibold">
                  Currency
                  <input
                    className="mt-1 w-full rounded-xl border p-3 uppercase"
                    defaultValue={selected.currency}
                    maxLength={3}
                    minLength={3}
                    name="currency"
                    required
                  />
                </label>
              </div>
              <div className="mt-5 flex flex-wrap gap-5 text-sm font-semibold">
                <label className="flex items-center gap-2">
                  <input
                    defaultChecked={selected.is_available}
                    name="is_available"
                    type="checkbox"
                  />{" "}
                  Available to order
                </label>
                <label className="flex items-center gap-2">
                  <input
                    defaultChecked={selected.is_active}
                    name="is_active"
                    type="checkbox"
                  />{" "}
                  Active model
                </label>
                <label className="flex items-center gap-2">
                  <input
                    defaultChecked={selected.is_clump}
                    name="is_clump"
                    type="checkbox"
                  />{" "}
                  Clump / package model
                </label>
                <label className="flex items-center gap-2">
                  <input
                    defaultChecked={selected.part_of_clump}
                    name="part_of_clump"
                    type="checkbox"
                  />{" "}
                  Component of a clump
                </label>
              </div>
              <button
                className="mt-6 rounded-xl bg-blue-800 px-5 py-3 font-bold text-white disabled:opacity-50"
                disabled={busy}
                type="submit"
              >
                {busy ? "Saving…" : "Save model"}
              </button>
            </form>

            <section className="rounded-2xl bg-white p-5 sm:p-6">
              <h2 className="text-xl font-bold">Cost history</h2>
              <p className="mt-1 text-sm text-slate-600">
                Price changes are retained here. Existing requests and purchase
                orders keep the cost captured when they were created.
              </p>
              <div className="mt-4 overflow-x-auto">
                <table className="w-full min-w-[640px] text-left text-sm">
                  <thead>
                    <tr className="border-b text-slate-500">
                      <th className="py-2">Cost</th>
                      <th>Effective from</th>
                      <th>Effective to</th>
                      <th>Source</th>
                    </tr>
                  </thead>
                  <tbody>
                    {history.map((cost) => (
                      <tr className="border-b" key={cost.id}>
                        <td className="py-3 font-semibold">
                          {money(cost.unit_price, cost.currency)}
                        </td>
                        <td>
                          {new Date(cost.effective_from).toLocaleString()}
                        </td>
                        <td>
                          {cost.effective_to
                            ? new Date(cost.effective_to).toLocaleString()
                            : "Current"}
                        </td>
                        <td className="capitalize">
                          {cost.source.replaceAll("-", " ")}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>
          </div>
        ) : (
          <section className="rounded-2xl bg-white p-8 text-center text-slate-600">
            No models found. Export the template, add model rows, and import the
            workbook.
          </section>
        )}
      </div>
    </main>
  );
}
