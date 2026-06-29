import { apiFetch } from "@/lib/api";

export type ReconciliationException = {
  id: string;
  exception_type: string;
  expected_amount: string;
  actual_amount: string;
  difference_amount: string;
  status: string;
  disposition: string | null;
};

export type Reconciliation = {
  id: string;
  invoice_id: string;
  purchase_order_id: string;
  status: string;
  decision_note: string | null;
  exceptions: ReconciliationException[];
};

export const listReconciliations = () =>
  apiFetch<Reconciliation[]>("/reconciliations");
export const createReconciliation = (invoiceId: string) =>
  apiFetch<Reconciliation>("/reconciliations", {
    method: "POST",
    body: JSON.stringify({ invoice_id: invoiceId }),
  });
export const resolveReconciliationException = (
  exceptionId: string,
  disposition: string,
  note: string,
) =>
  apiFetch<Reconciliation>(
    `/reconciliations/exceptions/${encodeURIComponent(exceptionId)}/resolution`,
    { method: "POST", body: JSON.stringify({ disposition, note }) },
  );
export const decideReconciliation = (
  caseId: string,
  action: "approve" | "reject",
  note: string,
) =>
  apiFetch<Reconciliation>(
    `/reconciliations/${encodeURIComponent(caseId)}/decision`,
    { method: "POST", body: JSON.stringify({ action, note }) },
  );
