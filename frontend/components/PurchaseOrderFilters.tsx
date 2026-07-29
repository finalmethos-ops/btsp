"use client";

import { FormEvent, useEffect, useState } from "react";
import { CatalogVendor, listVendors } from "@/lib/purchasing-api";
import { getPOStoreFilterOptions } from "@/lib/store-api";

export type PurchaseOrderFilterValues = {
  search: string;
  date_from: string;
  date_to: string;
  entity_code: string;
  region_code: string;
  store_number: string;
  vendor_code: string;
};

export const emptyPurchaseOrderFilters: PurchaseOrderFilterValues = {
  search: "",
  date_from: "",
  date_to: "",
  entity_code: "",
  region_code: "",
  store_number: "",
  vendor_code: "",
};

export function PurchaseOrderFilters({
  includeVendor = false,
  value,
  onChange,
}: {
  includeVendor?: boolean;
  value: PurchaseOrderFilterValues;
  onChange: (value: PurchaseOrderFilterValues) => void;
}) {
  const [draft, setDraft] = useState(value);
  const [vendors, setVendors] = useState<CatalogVendor[]>([]);
  const [entityOptions, setEntityOptions] = useState<
    { entity_code: string; regions: string[] }[]
  >([]);

  useEffect(() => setDraft(value), [value]);
  useEffect(() => {
    if (includeVendor) void listVendors().then(setVendors);
  }, [includeVendor]);
  useEffect(() => {
    void getPOStoreFilterOptions().then((options) =>
      setEntityOptions(options.entities),
    );
  }, []);

  const regionOptions =
    entityOptions.find((option) => option.entity_code === draft.entity_code)
      ?.regions ?? [];

  function submit(event: FormEvent) {
    event.preventDefault();
    onChange(draft);
  }

  const field = (key: keyof PurchaseOrderFilterValues, next: string) =>
    setDraft((current) => ({ ...current, [key]: next }));

  return (
    <form
      className="mt-5 rounded-2xl border border-slate-200 bg-white p-4"
      onSubmit={submit}
    >
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <input
          className="rounded-xl border p-3 sm:col-span-2"
          onChange={(event) => field("search", event.target.value)}
          placeholder="Search all or part of a PO number"
          value={draft.search}
        />
        <label className="text-xs font-bold text-slate-600">
          Created from
          <input
            className="mt-1 w-full rounded-xl border p-2.5 text-sm text-slate-950"
            onChange={(event) => field("date_from", event.target.value)}
            onClick={(event) => event.currentTarget.showPicker()}
            type="date"
            value={draft.date_from}
          />
        </label>
        <label className="text-xs font-bold text-slate-600">
          Created through
          <input
            className="mt-1 w-full rounded-xl border p-2.5 text-sm text-slate-950"
            onChange={(event) => field("date_to", event.target.value)}
            onClick={(event) => event.currentTarget.showPicker()}
            type="date"
            value={draft.date_to}
          />
        </label>
        <select
          className="rounded-xl border p-3"
          onChange={(event) =>
            setDraft((current) => ({
              ...current,
              entity_code: event.target.value,
              region_code: "",
              store_number: "",
            }))
          }
          value={draft.entity_code}
        >
          <option value="">All entities</option>
          {entityOptions.map((option) => (
            <option key={option.entity_code} value={option.entity_code}>
              {option.entity_code}
            </option>
          ))}
        </select>
        <select
          className="rounded-xl border p-3"
          disabled={!draft.entity_code}
          onChange={(event) => field("region_code", event.target.value)}
          value={draft.region_code}
        >
          <option value="">
            {draft.entity_code ? "All regions" : "Select an entity first"}
          </option>
          {regionOptions.map((region) => (
            <option key={region} value={region}>
              {region}
            </option>
          ))}
        </select>
        <input
          className="rounded-xl border p-3"
          onChange={(event) => field("store_number", event.target.value)}
          placeholder="Store number"
          value={draft.store_number}
        />
        {includeVendor ? (
          <select
            className="rounded-xl border p-3"
            onChange={(event) => field("vendor_code", event.target.value)}
            value={draft.vendor_code}
          >
            <option value="">All vendors</option>
            {vendors.map((vendor) => (
              <option key={vendor.vendor_code} value={vendor.vendor_code}>
                {vendor.name}
              </option>
            ))}
          </select>
        ) : null}
      </div>
      <div className="mt-3 flex gap-2">
        <button className="rounded-xl bg-blue-900 px-5 py-2 font-bold text-white">
          Search POs
        </button>
        <button
          className="rounded-xl bg-slate-100 px-5 py-2 font-bold"
          onClick={() => {
            setDraft(emptyPurchaseOrderFilters);
            onChange(emptyPurchaseOrderFilters);
          }}
          type="button"
        >
          Clear filters
        </button>
      </div>
    </form>
  );
}
