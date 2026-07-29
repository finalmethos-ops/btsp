"use client";

import Link from "next/link";
import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import { useAuth } from "@/lib/auth";
import {
  changeStoreStatus,
  getStoreDirectoryOptions,
  importStoreWorkbook,
  listManagedStores,
  saveStore,
  StoreRecord,
  StoreDirectoryOptions,
  StoreWrite,
} from "@/lib/store-api";

const emptyStore: StoreWrite = {
  store_number: "",
  name: "",
  region_code: "",
  operating_company: null,
  entity_code: null,
  purchasing_program: null,
  regional_manager_name: null,
  owner_operator_name: null,
  general_manager_name: null,
  manager_email: null,
  address_line1: null,
  city: null,
  state_code: null,
  postal_code: null,
  timezone: null,
  is_ordering_enabled: true,
  is_active: true,
  source_system: "purchasing_store_manager",
  source_updated_at: null,
};

const textFields: {
  key: keyof StoreWrite;
  label: string;
  required?: boolean;
}[] = [
  { key: "store_number", label: "Store Number", required: true },
  { key: "name", label: "Store Name", required: true },
  { key: "operating_company", label: "Operating Company" },
  { key: "regional_manager_name", label: "Regional Manager" },
  { key: "owner_operator_name", label: "Owner / Operator" },
  { key: "general_manager_name", label: "General Manager" },
  { key: "manager_email", label: "Manager Email" },
  { key: "address_line1", label: "Street Address" },
  { key: "city", label: "City" },
  { key: "state_code", label: "State" },
  { key: "postal_code", label: "ZIP Code" },
  { key: "timezone", label: "Time Zone" },
];

function toWrite(store: StoreRecord): StoreWrite {
  const {
    id: _id,
    created_at: _created,
    updated_at: _updated,
    ...values
  } = store;
  void _id;
  void _created;
  void _updated;
  return values;
}

export function StoreManagementWorkspace() {
  const { user } = useAuth();
  const canManage = user?.permissions.includes("stores.manage") ?? false;
  const [view, setView] = useState<"active" | "inactive">("active");
  const [stores, setStores] = useState<StoreRecord[]>([]);
  const [selected, setSelected] = useState<StoreRecord | null>(null);
  const [draft, setDraft] = useState<StoreWrite>(emptyStore);
  const [search, setSearch] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [directoryOptions, setDirectoryOptions] =
    useState<StoreDirectoryOptions>({
      entities: [],
      purchasing_programs: [],
      regions: [],
      entity_regions: {},
    });
  const load = useCallback(async () => {
    const next = await listManagedStores(view === "active");
    setStores(next);
    setSelected((current) => {
      const found = next.find(
        (item) => item.store_number === current?.store_number,
      );
      if (found) setDraft(toWrite(found));
      return found ?? null;
    });
  }, [view]);
  useEffect(() => {
    void load().catch((caught: unknown) =>
      setError(
        caught instanceof Error ? caught.message : "Unable to load stores",
      ),
    );
  }, [load]);
  useEffect(() => {
    void getStoreDirectoryOptions()
      .then(setDirectoryOptions)
      .catch(() => setError("Unable to load store directory options"));
  }, []);
  const filtered = useMemo(() => {
    const term = search.trim().toLowerCase();
    if (!term) return stores;
    return stores.filter((store) =>
      [
        store.store_number,
        store.name,
        store.entity_code,
        store.region_code,
        store.city,
        store.state_code,
      ].some((value) => value?.toLowerCase().includes(term)),
    );
  }, [search, stores]);
  function choose(store: StoreRecord) {
    setSelected(store);
    setDraft(toWrite(store));
    setError(null);
    setNotice(null);
  }
  function startNew() {
    setSelected(null);
    setDraft({ ...emptyStore });
    setError(null);
    setNotice(null);
  }
  function field(key: keyof StoreWrite, value: string | boolean) {
    setDraft((current) => ({
      ...current,
      [key]: typeof value === "string" && value === "" ? null : value,
    }));
  }
  async function run(operation: () => Promise<void>) {
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
  }
  async function submit(event: FormEvent) {
    event.preventDefault();
    await run(async () => {
      const saved = await saveStore({
        ...draft,
        store_number: String(draft.store_number),
        name: String(draft.name),
        region_code: String(draft.region_code),
        state_code: draft.state_code?.toUpperCase() ?? null,
        entity_code: draft.entity_code?.toUpperCase() ?? null,
        purchasing_program: draft.purchasing_program?.toUpperCase() ?? null,
      });
      await load();
      setSelected(saved);
      setDraft(toWrite(saved));
      setNotice(`Store ${saved.store_number} saved.`);
    });
  }
  async function upload(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const data = new FormData(form);
    const file = data.get("workbook");
    if (!(file instanceof File) || !file.size) return;
    await run(async () => {
      const result = await importStoreWorkbook(
        file,
        data.get("authoritative") === "on",
      );
      await load();
      form.reset();
      setNotice(
        `Imported ${result.upserted_rows} of ${result.total_rows} stores${result.failed_rows ? `; ${result.failed_rows} failed` : ""}.`,
      );
    });
  }

  return (
    <main className="mx-auto max-w-[1500px] p-4 sm:p-8">
      <Link className="text-sm text-slate-600" href="/">
        ← Command center
      </Link>
      <p className="brand-eyebrow mt-4">Purchasing</p>
      <h1 className="mt-2 text-3xl font-bold">Store Database</h1>
      <p className="mt-2 text-slate-600">
        {canManage
          ? "Maintain store authority records. Inactive stores are retained for history but removed from order creation."
          : "Search and review store authority records for reconciliation reference."}
      </p>
      {error ? (
        <p className="mt-4 rounded-xl bg-red-50 p-3 text-red-800">{error}</p>
      ) : null}
      {notice ? (
        <p className="mt-4 rounded-xl bg-green-50 p-3 text-green-800">
          {notice}
        </p>
      ) : null}

      {canManage ? (
        <form
          className="mt-5 flex flex-wrap items-center gap-3 rounded-2xl bg-white p-4"
          onSubmit={upload}
        >
          <strong>Import Current Store Workbook</strong>
          <input accept=".xlsx" name="workbook" required type="file" />
          <label className="flex items-center gap-2 text-sm">
            <input name="authoritative" type="checkbox" />
            Disable Stores Absent From Workbook
          </label>
          <button
            className="rounded-xl bg-blue-900 px-4 py-2 font-bold text-white"
            disabled={busy}
          >
            Import
          </button>
        </form>
      ) : null}

      <div className="mt-5 grid gap-5 lg:grid-cols-[360px_1fr]">
        <section className="rounded-2xl bg-white p-4">
          <div className="flex gap-2">
            {(["active", "inactive"] as const).map((option) => (
              <button
                className={`rounded-lg px-3 py-2 font-bold ${view === option ? "bg-yellow-400 text-slate-950" : "bg-slate-100"}`}
                key={option}
                onClick={() => {
                  setView(option);
                  setSelected(null);
                  setDraft({ ...emptyStore });
                }}
                type="button"
              >
                {option === "active" ? "Active Stores" : "Inactive History"}
              </button>
            ))}
          </div>
          <input
            className="mt-3 w-full rounded-xl border p-3"
            onChange={(event) => setSearch(event.target.value)}
            placeholder="Search Store, Entity, Region, City…"
            value={search}
          />
          {canManage ? (
            <button
              className="mt-3 w-full rounded-xl bg-yellow-400 p-3 font-bold text-slate-950"
              onClick={startNew}
              type="button"
            >
              Add New Store
            </button>
          ) : null}
          <p className="mt-3 text-xs text-slate-500">
            {filtered.length} stores
          </p>
          <div className="mt-2 max-h-[650px] overflow-y-auto">
            {filtered.map((store) => (
              <button
                className={`mb-2 w-full rounded-xl border p-3 text-left ${selected?.id === store.id ? "selected-object" : ""}`}
                key={store.id}
                onClick={() => choose(store)}
                type="button"
              >
                <strong>
                  {store.store_number} — {store.name}
                </strong>
                <span className="block text-xs text-slate-500">
                  {store.entity_code ?? "No entity"} · {store.region_code} ·{" "}
                  {store.city ?? "No city"}, {store.state_code ?? "—"}
                </span>
              </button>
            ))}
          </div>
        </section>

        <form className="rounded-2xl bg-white p-5" onSubmit={submit}>
          <div className="flex flex-wrap items-center justify-between gap-3">
            <h2 className="text-xl font-bold">
              {selected
                ? canManage
                  ? `Edit Store ${selected.store_number}`
                  : `Store ${selected.store_number} Details`
                : "Select A Store"}
            </h2>
            {selected && canManage ? (
              <button
                className="rounded-xl bg-yellow-400 px-4 py-2 font-bold text-slate-950"
                disabled={busy}
                onClick={() =>
                  void run(async () => {
                    await changeStoreStatus(
                      selected.store_number,
                      !selected.is_active,
                    );
                    setSelected(null);
                    setDraft({ ...emptyStore });
                    await load();
                    setNotice(
                      selected.is_active
                        ? "Store disabled and removed from ordering."
                        : "Store reactivated for ordering.",
                    );
                  })
                }
                type="button"
              >
                {selected.is_active ? "Disable Store" : "Reactivate Store"}
              </button>
            ) : null}
          </div>
          <div className="mt-5 grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            <label className="text-sm font-semibold">
              Entity
              <select
                className="mt-1 w-full rounded-xl border p-3 font-normal"
                disabled={!canManage}
                onChange={(event) =>
                  setDraft((current) => ({
                    ...current,
                    entity_code: event.target.value || null,
                    region_code: "",
                  }))
                }
                value={draft.entity_code ?? ""}
              >
                <option value="">Select Entity</option>
                {directoryOptions.entities.map((entity) => (
                  <option key={entity} value={entity}>
                    {entity}
                  </option>
                ))}
              </select>
            </label>
            <label className="text-sm font-semibold">
              Region
              <select
                className="mt-1 w-full rounded-xl border p-3 font-normal"
                disabled={!canManage || !draft.entity_code}
                onChange={(event) => field("region_code", event.target.value)}
                required
                value={draft.region_code ?? ""}
              >
                <option value="">
                  {draft.entity_code ? "Select Region" : "Select Entity First"}
                </option>
                {(
                  directoryOptions.entity_regions[draft.entity_code ?? ""] ?? []
                ).map((region) => (
                  <option key={region} value={region}>
                    {region}
                  </option>
                ))}
              </select>
            </label>
            <label className="text-sm font-semibold">
              Purchasing Program
              <select
                className="mt-1 w-full rounded-xl border p-3 font-normal"
                disabled={!canManage}
                onChange={(event) =>
                  field("purchasing_program", event.target.value)
                }
                value={draft.purchasing_program ?? ""}
              >
                <option value="">Select Purchasing Program</option>
                {directoryOptions.purchasing_programs.map((program) => (
                  <option key={program} value={program}>
                    {program}
                  </option>
                ))}
              </select>
            </label>
            {textFields.map(({ key, label, required }) => (
              <label className="text-sm font-semibold" key={key}>
                {label}
                <input
                  className="mt-1 w-full rounded-xl border p-3 font-normal"
                  disabled={
                    !canManage || (key === "store_number" && Boolean(selected))
                  }
                  inputMode={key === "store_number" ? "numeric" : undefined}
                  maxLength={key === "store_number" ? 4 : undefined}
                  onChange={(event) => field(key, event.target.value)}
                  pattern={key === "store_number" ? "[0-9]{4}" : undefined}
                  required={required}
                  type={key === "manager_email" ? "email" : "text"}
                  value={String(draft[key] ?? "")}
                />
              </label>
            ))}
          </div>
          <label className="mt-5 flex items-center gap-2 font-semibold">
            <input
              checked={draft.is_ordering_enabled}
              disabled={!canManage || !draft.is_active}
              onChange={(event) =>
                field("is_ordering_enabled", event.target.checked)
              }
              type="checkbox"
            />
            Enabled For Ordering
          </label>
          {canManage ? (
            <button
              className="mt-6 rounded-xl bg-blue-900 px-6 py-3 font-bold text-white"
              disabled={busy}
            >
              {selected ? "Save Changes" : "Create Store"}
            </button>
          ) : null}
        </form>
      </div>
    </main>
  );
}
