import { apiDownload, apiFetch } from "./api";

export type InvoiceIntakeDocument = {
  id: string;
  original_filename: string;
  page_start: number;
  page_end: number;
  invoice_number: string | null;
  detected_vendor_code: string | null;
  detected_store_number: string | null;
  detected_po_number: string | null;
  suggested_purchase_order_id: string | null;
  suggested_po_number: string | null;
  status: string;
  uploaded_by: string;
  uploader_vendor_code: string | null;
  created_at: string;
};

export type InvoiceIntakeBatch = {
  uploaded_files: number;
  separated_invoices: number;
  duplicate_invoices: number;
  documents: InvoiceIntakeDocument[];
};

export const listInvoiceIntake = () =>
  apiFetch<InvoiceIntakeDocument[]>("/invoice-intake");

export const uploadInvoicePDFs = (files: File[]) => {
  const body = new FormData();
  files.forEach((file) => body.append("files", file));
  return apiFetch<InvoiceIntakeBatch>("/invoice-intake/upload", {
    method: "POST",
    body,
  });
};

export const downloadInvoiceIntakePDF = (id: string) =>
  apiDownload(`/invoice-intake/${id}/pdf`);
