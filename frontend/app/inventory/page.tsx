"use client";

import { FormEvent, useState } from "react";
import { ProtectedRoute } from "@/components/ProtectedRoute";
import { PlatformSidebar } from "@/components/PlatformSidebar";
import {
  getInventoryPosition,
  postInventoryEntry,
  transferInventory,
  type InventoryPosition,
} from "@/lib/inventory-api";

export default function InventoryPage() {
  const [productCode, setProductCode] = useState("");
  const [storeNumber, setStoreNumber] = useState("");
  const [position, setPosition] = useState<InventoryPosition | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [transfer, setTransfer] = useState({ to: "", quantity: "" });

  async function lookup(event: FormEvent) {
    event.preventDefault();
    setError(null);
    try {
      setPosition(await getInventoryPosition(productCode, storeNumber));
    } catch (caught) {
      setError(
        caught instanceof Error ? caught.message : "Unable to load position.",
      );
    }
  }

  async function postAdjustment(event: FormEvent) {
    event.preventDefault();
    setError(null);
    try {
      await postInventoryEntry({
        product_code: productCode,
        store_number: storeNumber,
        quantity_delta: Number(transfer.quantity),
        reason: "adjustment",
      });
      setMessage("Inventory adjustment posted.");
      setPosition(await getInventoryPosition(productCode, storeNumber));
    } catch (caught) {
      setError(
        caught instanceof Error ? caught.message : "Unable to post adjustment.",
      );
    }
  }

  async function postTransfer(event: FormEvent) {
    event.preventDefault();
    setError(null);
    try {
      await transferInventory({
        product_code: productCode,
        from_store_number: storeNumber,
        to_store_number: transfer.to,
        quantity: Number(transfer.quantity),
      });
      setMessage("Inventory transfer posted.");
      setPosition(await getInventoryPosition(productCode, storeNumber));
    } catch (caught) {
      setError(
        caught instanceof Error ? caught.message : "Unable to post transfer.",
      );
    }
  }

  return (
    <ProtectedRoute requiredPermission="receiving.read">
      <div className="platform-shell">
        <PlatformSidebar />
        <main className="platform-main space-y-6 p-6">
          <div>
            <p className="eyebrow">INVENTORY LEDGER</p>
            <h1>Inventory position</h1>
            <p>
              Track on-hand, reserved, transferred, and adjusted quantities by
              store.
            </p>
          </div>
          <form
            className="glass-panel grid gap-3 md:grid-cols-3"
            onSubmit={lookup}
          >
            <input
              value={productCode}
              onChange={(event) => setProductCode(event.target.value)}
              placeholder="Product code"
              required
            />
            <input
              value={storeNumber}
              onChange={(event) => setStoreNumber(event.target.value)}
              placeholder="Store number"
              required
            />
            <button className="button-primary" type="submit">
              Load position
            </button>
          </form>
          {position ? (
            <section className="grid gap-3 md:grid-cols-3">
              {[
                ["On hand", position.on_hand],
                ["Reserved", position.reserved],
                ["Available", position.available],
              ].map(([label, value]) => (
                <article className="metric-card" key={label}>
                  <span>{label}</span>
                  <strong>{value}</strong>
                </article>
              ))}
            </section>
          ) : null}
          <section className="glass-panel grid gap-4 md:grid-cols-2">
            <form className="space-y-3" onSubmit={postAdjustment}>
              <h2>Post adjustment</h2>
              <input
                type="number"
                step="1"
                placeholder="Quantity (+/-)"
                value={transfer.quantity}
                onChange={(event) =>
                  setTransfer({ ...transfer, quantity: event.target.value })
                }
                required
              />
              <button className="button-primary" type="submit">
                Post adjustment
              </button>
            </form>
            <form className="space-y-3" onSubmit={postTransfer}>
              <h2>Transfer stock</h2>
              <input
                placeholder="Destination store"
                value={transfer.to}
                onChange={(event) =>
                  setTransfer({ ...transfer, to: event.target.value })
                }
                required
              />
              <button className="button-primary" type="submit">
                Transfer quantity
              </button>
            </form>
          </section>
          {message ? <p className="text-green-300">{message}</p> : null}
          {error ? <p className="text-red-300">{error}</p> : null}
        </main>
      </div>
    </ProtectedRoute>
  );
}
