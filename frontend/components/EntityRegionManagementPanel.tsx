"use client";
import { FormEvent, useEffect, useState } from "react";
import {
  EntityRegion,
  createEntityRegion,
  deleteEntityRegion,
  listEntityRegions,
} from "@/lib/store-api";
export function EntityRegionManagementPanel() {
  const [items, setItems] = useState<EntityRegion[]>([]);
  const [entityCode, setEntityCode] = useState("");
  const [regionCode, setRegionCode] = useState("");
  async function refresh() {
    setItems(await listEntityRegions());
  }
  useEffect(() => void refresh(), []);
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    await createEntityRegion(entityCode, regionCode);
    setEntityCode("");
    setRegionCode("");
    await refresh();
  }
  return (
    <section className="mt-10">
      <h2 className="text-2xl font-bold">Entities and regions</h2>
      <p className="mt-2 text-sm text-slate-600">
        Maintain approved internal organization and regional assignments.
      </p>
      <form
        className="mt-4 flex flex-wrap gap-3"
        onSubmit={(event) => void submit(event)}
      >
        <input
          className="rounded border px-3 py-2"
          placeholder="Entity"
          required
          value={entityCode}
          onChange={(event) => setEntityCode(event.target.value.toUpperCase())}
        />
        <input
          className="rounded border px-3 py-2"
          placeholder="Region"
          required
          value={regionCode}
          onChange={(event) => setRegionCode(event.target.value.toUpperCase())}
        />
        <button className="user-directory-save rounded px-4 py-2 font-semibold">
          Add region
        </button>
      </form>
      <div className="mt-4 flex flex-wrap gap-2">
        {items.map((item) => (
          <button
            className="selection-pane rounded border px-3 py-2 text-sm"
            key={`${item.entity_code}-${item.region_code}`}
            onClick={() =>
              void deleteEntityRegion(item.entity_code, item.region_code).then(
                refresh,
              )
            }
            type="button"
          >
            {item.entity_code} · {item.region_code} ×
          </button>
        ))}
      </div>
    </section>
  );
}
