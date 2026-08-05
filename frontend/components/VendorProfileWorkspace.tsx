"use client";

import Link from "next/link";
import { FormEvent, useCallback, useEffect, useState } from "react";
import {
  getVendorStateExclusions,
  getVendorPOEmailPreference,
  listVendorMOQRules,
  saveVendorStateExclusions,
  saveVendorPOEmailPreference,
  saveVendorMOQRule,
  setMOQContributors,
  VendorMOQRule,
} from "@/lib/vendor-model-api";

const US_STATES = [
  "AL",
  "AK",
  "AZ",
  "AR",
  "CA",
  "CO",
  "CT",
  "DE",
  "FL",
  "GA",
  "HI",
  "ID",
  "IL",
  "IN",
  "IA",
  "KS",
  "KY",
  "LA",
  "ME",
  "MD",
  "MA",
  "MI",
  "MN",
  "MS",
  "MO",
  "MT",
  "NE",
  "NV",
  "NH",
  "NJ",
  "NM",
  "NY",
  "NC",
  "ND",
  "OH",
  "OK",
  "OR",
  "PA",
  "RI",
  "SC",
  "SD",
  "TN",
  "TX",
  "UT",
  "VT",
  "VA",
  "WA",
  "WV",
  "WI",
  "WY",
  "DC",
];

export function VendorProfileWorkspace() {
  const [rules, setRules] = useState<VendorMOQRule[]>([]);
  const [selected, setSelected] = useState<VendorMOQRule | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [excludedStates, setExcludedStates] = useState<string[]>([]);
  const [poEmail, setPoEmail] = useState("");
  const [thresholdType, setThresholdType] = useState<
    "unit_quantity" | "order_amount"
  >("order_amount");
  const load = useCallback(async () => {
    const [next, geography, emailPreference] = await Promise.all([
      listVendorMOQRules(),
      getVendorStateExclusions(),
      getVendorPOEmailPreference(),
    ]);
    setRules(next);
    setExcludedStates(geography.state_codes);
    setPoEmail(emailPreference.po_email_recipient ?? "");
    setSelected(
      (current) => next.find((r) => r.id === current?.id) ?? next[0] ?? null,
    );
  }, []);
  useEffect(() => {
    void load();
  }, [load]);
  useEffect(() => {
    setThresholdType(selected?.threshold_type ?? "order_amount");
  }, [selected]);

  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    setError(null);
    setMessage(null);
    try {
      const rule = await saveVendorMOQRule({
        id: selected?.id,
        code: String(data.get("code")).trim(),
        name: String(data.get("name")).trim(),
        threshold_type: String(data.get("threshold_type")) as
          | "unit_quantity"
          | "order_amount",
        threshold_value: Number(data.get("threshold_value")),
        is_active: data.get("is_active") === "on",
      });
      const contributors = rules
        .filter((item) => data.get(`source-${item.id}`) === "on")
        .map((item) => item.id);
      await setMOQContributors(rule.id, contributors);
      const refreshed = await listVendorMOQRules();
      setRules(refreshed);
      setSelected(refreshed.find((item) => item.id === rule.id) ?? null);
      setMessage("MOQ profile saved.");
    } catch (caught) {
      setError(
        caught instanceof Error
          ? caught.message
          : "Unable to save the MOQ profile.",
      );
    }
  }

  async function saveGeography() {
    setError(null);
    setMessage(null);
    try {
      const result = await saveVendorStateExclusions(excludedStates);
      setExcludedStates(result.state_codes);
      setMessage(
        "Geographical exclusions saved. Store selectors now reflect this service area.",
      );
    } catch (caught) {
      setError(
        caught instanceof Error
          ? caught.message
          : "Unable to save the exclusions.",
      );
    }
  }

  return (
    <main className="mx-auto max-w-6xl p-4 sm:p-8">
      <Link className="text-sm text-slate-600" href="/">
        ← Command center
      </Link>
      <p className="brand-eyebrow mt-4">Vendor settings</p>
      <h1 className="mt-2 text-3xl font-bold">Vendor profile and MOQ rules</h1>
      <p className="mt-2 text-slate-600">
        Create unit or dollar minimums. Contributions are directional: checking
        a source below means it counts toward this target rule only.
      </p>
      {message ? (
        <p className="mt-4 rounded-xl bg-green-50 p-3 text-green-800">
          {message}
        </p>
      ) : null}
      {error ? (
        <p className="mt-4 rounded-xl bg-red-50 p-3 text-red-800">{error}</p>
      ) : null}
      <div className="mt-6 grid gap-5 lg:grid-cols-[300px_1fr]">
        <section className="rounded-2xl bg-white p-4">
          <button
            className="mb-3 w-full rounded-xl bg-blue-800 p-3 font-bold text-white"
            onClick={() => setSelected(null)}
          >
            + New MOQ rule
          </button>
          {rules.map((rule) => (
            <button
              className={`mb-2 w-full rounded-xl border p-3 text-left ${selected?.id === rule.id ? "selected-object" : ""}`}
              key={rule.id}
              onClick={() => setSelected(rule)}
            >
              <strong>{rule.name}</strong>
              <span className="block text-xs text-slate-500">
                {rule.code} ·{" "}
                {rule.threshold_type === "order_amount" ? "$" : ""}
                {rule.threshold_type === "unit_quantity"
                  ? Math.trunc(Number(rule.threshold_value))
                  : Number(rule.threshold_value).toFixed(2)}
                {rule.threshold_type === "unit_quantity" ? " units" : ""}
              </span>
            </button>
          ))}
        </section>
        <form
          className="rounded-2xl bg-white p-6"
          key={selected?.id ?? "new"}
          onSubmit={save}
        >
          <h2 className="text-xl font-bold">
            {selected ? "Edit MOQ rule" : "New MOQ rule"}
          </h2>
          <div className="mt-4 grid gap-4 sm:grid-cols-2">
            <label className="text-sm font-semibold">
              Code
              <input
                className="mt-1 w-full rounded-xl border p-3"
                defaultValue={selected?.code}
                name="code"
                required
              />
            </label>
            <label className="text-sm font-semibold">
              Name
              <input
                className="mt-1 w-full rounded-xl border p-3"
                defaultValue={selected?.name}
                name="name"
                required
              />
            </label>
            <label className="text-sm font-semibold">
              Minimum type
              <select
                className="mt-1 w-full rounded-xl border p-3"
                name="threshold_type"
                onChange={(event) =>
                  setThresholdType(
                    event.target.value as "unit_quantity" | "order_amount",
                  )
                }
                value={thresholdType}
              >
                <option value="unit_quantity">Unit quantity</option>
                <option value="order_amount">Dollar amount</option>
              </select>
            </label>
            <label className="text-sm font-semibold">
              Minimum value
              <input
                className="mt-1 w-full rounded-xl border p-3"
                defaultValue={
                  selected
                    ? thresholdType === "unit_quantity"
                      ? Math.trunc(Number(selected.threshold_value))
                      : Number(selected.threshold_value).toFixed(2)
                    : thresholdType === "unit_quantity"
                      ? "0"
                      : "0.00"
                }
                inputMode={
                  thresholdType === "unit_quantity" ? "numeric" : "decimal"
                }
                key={`${selected?.id ?? "new"}-${thresholdType}`}
                min="0"
                name="threshold_value"
                required
                step={thresholdType === "unit_quantity" ? "1" : "0.01"}
                type="number"
              />
            </label>
          </div>
          <label className="mt-4 flex gap-2 text-sm font-semibold">
            <input
              defaultChecked={selected?.is_active ?? true}
              name="is_active"
              type="checkbox"
            />{" "}
            Active
          </label>
          {selected ? (
            <fieldset className="mt-6">
              <legend className="font-bold">
                Rules that can contribute toward this MOQ
              </legend>
              <p className="mb-3 text-sm text-slate-500">
                This does not automatically allow this MOQ to contribute back.
              </p>
              {rules
                .filter((r) => r.id !== selected.id)
                .map((rule) => (
                  <label className="mb-2 flex gap-2 text-sm" key={rule.id}>
                    <input
                      defaultChecked={selected.contributor_rule_ids.includes(
                        rule.id,
                      )}
                      name={`source-${rule.id}`}
                      type="checkbox"
                    />
                    {rule.name}
                  </label>
                ))}
            </fieldset>
          ) : null}
          <button className="mt-6 rounded-xl bg-blue-800 px-5 py-3 font-bold text-white">
            Save MOQ rule
          </button>
        </form>
      </div>
      <section className="mt-6 rounded-2xl bg-white p-6">
        <h2 className="text-xl font-bold">Geographical exclusions</h2>
        <p className="mt-1 text-sm text-slate-600">
          Select states this vendor does not serve. Stores in these states are
          removed from order selectors and blocked by purchasing validation.
        </p>
        <div className="mt-5 grid grid-cols-3 gap-2 sm:grid-cols-6 md:grid-cols-9">
          {US_STATES.map((code) => (
            <label
              className={`selection-pane flex cursor-pointer items-center gap-2 rounded-lg border p-2 text-sm ${excludedStates.includes(code) ? "is-selected font-semibold" : ""}`}
              key={code}
            >
              <input
                checked={excludedStates.includes(code)}
                onChange={(event) =>
                  setExcludedStates((current) =>
                    event.target.checked
                      ? [...current, code]
                      : current.filter((item) => item !== code),
                  )
                }
                type="checkbox"
              />
              {code}
            </label>
          ))}
        </div>
        <button
          className="mt-5 rounded-xl bg-blue-800 px-5 py-3 font-bold text-white"
          onClick={() => void saveGeography()}
          type="button"
        >
          Save exclusions
        </button>
      </section>
      <section className="mt-6 rounded-2xl bg-white p-6">
        <h2 className="text-xl font-bold">PO email recipient</h2>
        <p className="mt-1 text-sm text-slate-600">
          Default recipient used when preparing a PO email from the Accept PO
          module.
        </p>
        <div className="mt-4 flex flex-wrap gap-3">
          <input
            className="min-w-72 flex-1 rounded-xl border p-3"
            onChange={(event) => setPoEmail(event.target.value)}
            placeholder="orders@example.com"
            type="email"
            value={poEmail}
          />
          <button
            className="rounded-xl bg-blue-800 px-5 py-3 font-bold text-white"
            onClick={() =>
              void saveVendorPOEmailPreference(poEmail.trim() || null).then(
                () => setMessage("PO email preference saved."),
              )
            }
            type="button"
          >
            Save email
          </button>
        </div>
      </section>
    </main>
  );
}
