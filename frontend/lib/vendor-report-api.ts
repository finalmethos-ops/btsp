import { apiFetch } from "./api";

export type VendorReport = {
  vendor_code: string;
  selected_year: number;
  available_years: number[];
  purchase_order_count: number;
  active_po_count: number;
  attention_po_count: number;
  rejected_or_cancelled_count: number;
  units_ordered: string;
  units_received: string;
  fill_rate: string | null;
  unreconciled_invoice_count: number;
  annual_spend: { currency: string; amount: string }[];
  average_po_value: { currency: string; amount: string }[];
  monthly_spend: {
    month: number;
    currency: string;
    purchase_order_count: number;
    quantity: string;
    received_quantity: string;
    spend: string;
  }[];
  category_spend: {
    department: string;
    product_code: string;
    currency: string;
    purchase_order_count: number;
    quantity: string;
    spend: string;
  }[];
};

export const getVendorReport = (year?: number) =>
  apiFetch<VendorReport>(`/vendor-reports${year ? `?year=${year}` : ""}`);
