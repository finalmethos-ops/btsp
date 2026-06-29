import { apiFetch } from "@/lib/api";

export type VendorInvoice = {
  id: string;
  invoice_number: string;
  vendor_code: string;
  purchase_order_id: string;
  invoice_date: string;
  currency: string;
  total: string;
  status: string;
  lines: Array<{
    id: number;
    product_code: string;
    quantity: string;
    unit_price: string;
    match: {
      quantity_difference: string;
      price_difference: string;
      status: string;
    };
  }>;
};

export const listInvoices = () => apiFetch<VendorInvoice[]>("/invoices");
export const createInvoice = (payload: Record<string, unknown>) =>
  apiFetch<VendorInvoice>("/invoices", {
    method: "POST",
    body: JSON.stringify(payload),
  });
