import { apiFetch } from "./api";

export type InventoryPosition = {
  product_code: string;
  store_number: string;
  on_hand: string;
  reserved: string;
  available: string;
};

export async function getInventoryPosition(
  productCode: string,
  storeNumber: string,
) {
  return apiFetch<InventoryPosition>(
    `/inventory/position?product_code=${encodeURIComponent(productCode)}&store_number=${encodeURIComponent(storeNumber)}`,
  );
}

export async function postInventoryEntry(payload: {
  product_code: string;
  store_number: string;
  quantity_delta: number;
  reason: string;
}) {
  return apiFetch("/inventory/ledger", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function transferInventory(payload: {
  product_code: string;
  from_store_number: string;
  to_store_number: string;
  quantity: number;
}) {
  return apiFetch("/inventory/transfers", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}
