const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "";
const TOKEN_STORAGE_KEY = "btsp.access_token";

export type LoginResponse = {
  access_token: string;
  token_type: string;
};

export type CurrentUser = {
  email: string;
  display_name: string;
  roles: string[];
  permissions: string[];
  workflows: string[];
};

export type AvailableWorkflow = {
  code: string;
  name: string;
  route: string;
};

export type AdminUser = {
  id: number;
  email: string;
  display_name: string;
  home_store_number: string | null;
  region_code: string | null;
  is_active: boolean;
  roles: string[];
  permissions: string[];
};

export type AdminUserCreate = {
  email: string;
  display_name: string;
  password: string;
  home_store_number?: string | null;
  region_code?: string | null;
  is_active: boolean;
  role_codes: string[];
};

export type AdminUserUpdate = {
  display_name?: string;
  home_store_number?: string | null;
  region_code?: string | null;
  is_active?: boolean;
  role_codes?: string[];
};

export type AdminPermission = {
  code: string;
  description: string;
};

export type AdminRole = {
  id: number;
  code: string;
  name: string;
  workflow_code: string | null;
  is_system_role: boolean;
  permission_codes: string[];
  user_count: number;
};

export type AdminRoleCreate = {
  code: string;
  name: string;
  workflow_code?: string | null;
  permission_codes: string[];
};

export type AdminRoleUpdate = {
  name?: string;
  workflow_code?: string | null;
  permission_codes?: string[];
};

export type WorkflowDefinitionAdmin = {
  id: number;
  code: string;
  name: string;
  version: number;
  business_area: string | null;
  category: string | null;
  configuration_namespace: string | null;
  states: string[];
  initial_state: string;
  terminal_states: string[];
  transitions: Array<Record<string, unknown>>;
  is_active: boolean;
  active_instance_count: number;
  total_instance_count: number;
  created_at: string;
  updated_at: string;
};

export type NotificationTemplateAdmin = {
  id: number;
  template_code: string;
  workflow_code: string;
  event_type: string;
  channel: "in_app" | "email" | "webhook";
  subject_template: string;
  body_template: string;
  recipient_strategy:
    | "actor"
    | "workflow_role"
    | "permission_holders"
    | "region_admins"
    | "store_users"
    | "static_recipients";
  recipient_config: Record<string, unknown>;
  is_active: boolean;
  created_at: string;
  updated_at: string;
};

export type NotificationEventAdmin = {
  notification_id: number;
  template_code: string;
  workflow_code: string;
  event_type: string;
  entity_type: string;
  entity_id: string;
  actor: string;
  channel: string;
  recipient_strategy: string;
  resolved_recipients: string[];
  subject: string;
  body: string;
  status: "queued" | "sent" | "skipped" | "failed";
  error_message: string | null;
  created_at: string;
  sent_at: string | null;
};

export type NotificationTemplateAdminWrite = Omit<
  NotificationTemplateAdmin,
  "id" | "created_at" | "updated_at"
>;

export type SystemDiagnostics = {
  status: "healthy" | "degraded" | "unavailable";
  application: string;
  version: string;
  environment: string;
  database_revision: string | null;
  uptime_seconds: number;
  generated_at: string;
  dependencies: Array<{
    name: string;
    status: "healthy" | "degraded" | "unavailable";
    latency_ms: number | null;
    detail: string | null;
  }>;
  storage: Array<{
    name: string;
    status: "healthy" | "degraded" | "unavailable";
    writable: boolean;
    free_bytes: number | null;
  }>;
  operational_metrics: Array<{
    name: string;
    count: number;
    severity: "info" | "warning";
  }>;
};

export type AuditEvent = {
  id: number;
  event_type: string;
  entity_type: string;
  entity_id: string;
  actor: string;
  payload: Record<string, unknown>;
  created_at: string;
};

export type AuditEventPage = {
  items: AuditEvent[];
  total: number;
  limit: number;
  offset: number;
};

export type AuditSummary = {
  total: number;
  date_from: string | null;
  date_to: string | null;
  event_types: Array<{ key: string; count: number }>;
  entity_types: Array<{ key: string; count: number }>;
  actors: Array<{ key: string; count: number }>;
};

export type AuditFilters = {
  event_type?: string;
  entity_type?: string;
  entity_id?: string;
  actor?: string;
  date_from?: string;
  date_to?: string;
};

export function getStoredToken(): string | null {
  if (typeof window === "undefined") {
    return null;
  }
  try {
    return window.localStorage.getItem(TOKEN_STORAGE_KEY);
  } catch {
    return null;
  }
}

export function storeToken(token: string): void {
  try {
    window.localStorage.setItem(TOKEN_STORAGE_KEY, token);
  } catch {
    throw new Error(
      "Browser storage is unavailable; enable site storage to sign in",
    );
  }
}

export function clearToken(): void {
  try {
    window.localStorage.removeItem(TOKEN_STORAGE_KEY);
  } catch {
    // Storage may be blocked by browser privacy settings. There is no token to clear in that case.
  }
}

export async function apiFetch<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const token = getStoredToken();
  const usesFormData =
    typeof FormData !== "undefined" && options.body instanceof FormData;
  const response = await fetch(`${API_BASE_URL}/api/v1${path}`, {
    ...options,
    headers: {
      ...(!usesFormData ? { "Content-Type": "application/json" } : {}),
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options.headers,
    },
  });

  if (!response.ok) {
    const detail = (await response.json().catch(() => null)) as {
      detail?: string;
    } | null;
    throw new Error(
      detail?.detail ??
        `BTSP API request failed with status ${response.status}`,
    );
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

export async function apiDownload(path: string): Promise<Blob> {
  const token = getStoredToken();
  const response = await fetch(`${API_BASE_URL}/api/v1${path}`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });
  if (!response.ok)
    throw new Error(`BTSP download failed with status ${response.status}`);
  return response.blob();
}

export async function login(
  email: string,
  password: string,
): Promise<LoginResponse> {
  return apiFetch<LoginResponse>("/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
}

export async function getCurrentUser(): Promise<CurrentUser> {
  return apiFetch<CurrentUser>("/auth/me");
}

export async function getAvailableWorkflows(): Promise<AvailableWorkflow[]> {
  return apiFetch<AvailableWorkflow[]>("/workflows/available");
}

export async function listAdminUsers(): Promise<AdminUser[]> {
  return apiFetch<AdminUser[]>("/users");
}

export async function createAdminUser(
  payload: AdminUserCreate,
): Promise<AdminUser> {
  return apiFetch<AdminUser>("/users", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function updateAdminUser(
  email: string,
  payload: AdminUserUpdate,
): Promise<AdminUser> {
  return apiFetch<AdminUser>(`/users/${encodeURIComponent(email)}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export async function listAdminRoles(): Promise<AdminRole[]> {
  return apiFetch<AdminRole[]>("/roles");
}

export async function listAdminPermissions(): Promise<AdminPermission[]> {
  return apiFetch<AdminPermission[]>("/roles/permissions");
}

export async function createAdminRole(
  payload: AdminRoleCreate,
): Promise<AdminRole> {
  return apiFetch<AdminRole>("/roles", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function updateAdminRole(
  code: string,
  payload: AdminRoleUpdate,
): Promise<AdminRole> {
  return apiFetch<AdminRole>(`/roles/${encodeURIComponent(code)}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export async function deleteAdminRole(code: string): Promise<void> {
  return apiFetch<void>(`/roles/${encodeURIComponent(code)}`, {
    method: "DELETE",
  });
}

export async function listWorkflowDefinitionsAdmin(): Promise<
  WorkflowDefinitionAdmin[]
> {
  return apiFetch<WorkflowDefinitionAdmin[]>("/workflow-admin/definitions");
}

export async function setWorkflowDefinitionActivation(
  workflowCode: string,
  version: number,
  isActive: boolean,
): Promise<WorkflowDefinitionAdmin> {
  return apiFetch<WorkflowDefinitionAdmin>(
    `/workflow-admin/definitions/${encodeURIComponent(workflowCode)}/versions/${version}/activation`,
    {
      method: "PATCH",
      body: JSON.stringify({ is_active: isActive }),
    },
  );
}

export async function listNotificationTemplatesAdmin(): Promise<
  NotificationTemplateAdmin[]
> {
  return apiFetch<NotificationTemplateAdmin[]>("/notifications/templates");
}

export async function createNotificationTemplateAdmin(
  payload: NotificationTemplateAdminWrite,
): Promise<NotificationTemplateAdmin> {
  return apiFetch<NotificationTemplateAdmin>("/notifications/templates", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function updateNotificationTemplateAdmin(
  templateCode: string,
  payload: Partial<Omit<NotificationTemplateAdminWrite, "template_code">>,
): Promise<NotificationTemplateAdmin> {
  return apiFetch<NotificationTemplateAdmin>(
    `/notifications/templates/${encodeURIComponent(templateCode)}`,
    { method: "PATCH", body: JSON.stringify(payload) },
  );
}

export async function listNotificationEventsAdmin(): Promise<
  NotificationEventAdmin[]
> {
  return apiFetch<NotificationEventAdmin[]>("/notifications/events?limit=100");
}

export async function retryNotificationEventAdmin(
  notificationId: number,
): Promise<NotificationEventAdmin> {
  return apiFetch<NotificationEventAdmin>(
    `/notifications/events/${notificationId}/retry`,
    { method: "POST" },
  );
}

export async function getSystemDiagnostics(): Promise<SystemDiagnostics> {
  return apiFetch<SystemDiagnostics>("/system/diagnostics");
}

function auditQuery(filters: AuditFilters): string {
  const query = new URLSearchParams();
  Object.entries(filters).forEach(([key, value]) => {
    if (value) query.set(key, value);
  });
  return query.toString();
}

export async function listAuditEvents(
  filters: AuditFilters,
  limit = 50,
  offset = 0,
): Promise<AuditEventPage> {
  const query = auditQuery(filters);
  return apiFetch<AuditEventPage>(
    `/audit/events?${query ? `${query}&` : ""}limit=${limit}&offset=${offset}`,
  );
}

export async function getAuditSummary(
  filters: AuditFilters,
): Promise<AuditSummary> {
  const query = auditQuery(filters);
  return apiFetch<AuditSummary>(`/audit/summary${query ? `?${query}` : ""}`);
}

export async function downloadAuditExport(
  filters: AuditFilters,
): Promise<Blob> {
  const query = auditQuery(filters);
  return apiDownload(`/audit/export${query ? `?${query}` : ""}`);
}
