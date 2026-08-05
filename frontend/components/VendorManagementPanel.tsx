"use client";

import { FormEvent, useEffect, useState } from "react";
import {
  CatalogVendor,
  createCatalogVendor,
  listVendors,
  updateCatalogVendor,
} from "@/lib/purchasing-api";

export function VendorManagementPanel() {
  const [vendors, setVendors] = useState<CatalogVendor[]>([]);
  const [vendorCode, setVendorCode] = useState("");
  const [name, setName] = useState("");
  const [notice, setNotice] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function refresh() {
    setVendors(await listVendors(false));
  }

  useEffect(() => {
    void refresh().catch(() => setError("Unable to load vendors."));
  }, []);

  async function create(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setNotice(null);
    setError(null);
    try {
      await createCatalogVendor(vendorCode, name);
      setVendorCode("");
      setName("");
      await refresh();
      setNotice("Vendor added to the active directory.");
    } catch (caught) {
      setError(
        caught instanceof Error ? caught.message : "Unable to add vendor.",
      );
    }
  }

  async function toggle(vendor: CatalogVendor) {
    setNotice(null);
    setError(null);
    try {
      await updateCatalogVendor(vendor.vendor_code, {
        is_active: !vendor.is_active,
      });
      await refresh();
    } catch (caught) {
      setError(
        caught instanceof Error ? caught.message : "Unable to update vendor.",
      );
    }
  }

  return (
    <section className="mt-10">
      <h2 className="text-2xl font-bold">Vendor directory</h2>
      <p className="mt-2 text-sm text-slate-600">
        Add vendors or control whether they appear in active purchasing lists.
        Inactive vendors remain available for historical records.
      </p>
      <form
        className="mt-5 grid gap-3 rounded-xl border border-slate-200 p-4 md:grid-cols-[1fr_2fr_auto]"
        onSubmit={create}
      >
        <input
          className="rounded border border-slate-300 px-3 py-2"
          maxLength={64}
          onChange={(event) =>
            setVendorCode(
              event.target.value
                .toUpperCase()
                .replace(/[^A-Z0-9]+/g, "-")
                .replace(/^-|-$/g, ""),
            )
          }
          placeholder="Vendor code"
          required
          value={vendorCode}
        />
        <input
          className="rounded border border-slate-300 px-3 py-2"
          maxLength={255}
          onChange={(event) => setName(event.target.value)}
          placeholder="Vendor name"
          required
          value={name}
        />
        <button className="rounded bg-blue-900 px-5 py-2 font-bold text-white">
          Add vendor
        </button>
      </form>
      {notice ? <p className="mt-3 text-sm text-green-700">{notice}</p> : null}
      {error ? <p className="mt-3 text-sm text-red-700">{error}</p> : null}
      <div className="mt-5 overflow-x-auto rounded-xl border border-slate-200">
        <table className="w-full border-collapse text-left text-sm">
          <thead className="bg-slate-100">
            <tr>
              <th className="p-3">Vendor</th>
              <th className="p-3">Code</th>
              <th className="p-3">Status</th>
              <th className="p-3">Action</th>
            </tr>
          </thead>
          <tbody>
            {vendors.map((vendor) => (
              <tr
                className="border-t border-slate-200"
                key={vendor.vendor_code}
              >
                <td className="p-3 font-medium">{vendor.name}</td>
                <td className="p-3">{vendor.vendor_code}</td>
                <td className="p-3">
                  {vendor.is_active ? "Active" : "Inactive"}
                </td>
                <td className="p-3">
                  <button
                    className={`rounded px-3 py-2 font-semibold ${
                      vendor.is_active
                        ? "bg-slate-200 text-slate-800"
                        : "bg-yellow-400 text-slate-950"
                    }`}
                    onClick={() => void toggle(vendor)}
                    type="button"
                  >
                    {vendor.is_active ? "Deactivate" : "Activate"}
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
