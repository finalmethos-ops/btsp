import { apiFetch } from "@/lib/api";

export type VendorEndpoint = {
  id: string;
  vendor_code: string;
  name: string;
  transport: string;
  direction: string;
  is_active: boolean;
};

export type ConnectorSchedule = {
  id: string;
  endpoint_id: string;
  name: string;
  interval_minutes: number;
  max_attempts: number;
  base_retry_seconds: number;
  is_enabled: boolean;
  next_run_at: string;
};

export type ConnectorExecution = {
  id: string;
  schedule_id: string;
  endpoint_id: string;
  import_run_id: string | null;
  status: string;
  scheduled_for: string;
  available_at: string;
  attempt_count: number;
  max_attempts: number;
  worker_id: string | null;
  lease_expires_at: string | null;
  error_message: string | null;
};

export const listVendorEndpoints = () =>
  apiFetch<VendorEndpoint[]>("/vendor-integrations/endpoints");

export const listConnectorSchedules = () =>
  apiFetch<ConnectorSchedule[]>("/vendor-integrations/connector-schedules");

export const createConnectorSchedule = (payload: {
  endpoint_id: string;
  name: string;
  interval_minutes: number;
  max_attempts: number;
  base_retry_seconds: number;
}) =>
  apiFetch<ConnectorSchedule>("/vendor-integrations/connector-schedules", {
    method: "POST",
    body: JSON.stringify(payload),
  });

export const setConnectorScheduleEnabled = (
  scheduleId: string,
  isEnabled: boolean,
) =>
  apiFetch<ConnectorSchedule>(
    `/vendor-integrations/connector-schedules/${encodeURIComponent(scheduleId)}`,
    {
      method: "PATCH",
      body: JSON.stringify({ is_enabled: isEnabled }),
    },
  );

export const listConnectorExecutions = () =>
  apiFetch<ConnectorExecution[]>("/vendor-integrations/connector-executions");

export const enqueueDueConnectorExecutions = () =>
  apiFetch<ConnectorExecution[]>(
    "/vendor-integrations/connector-executions/enqueue-due",
    { method: "POST" },
  );

export const replayConnectorExecution = (executionId: string) =>
  apiFetch<ConnectorExecution>(
    `/vendor-integrations/connector-executions/${encodeURIComponent(executionId)}/replay`,
    { method: "POST" },
  );
