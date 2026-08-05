import { getApiBaseUrl } from "./api-origin";

const TOKEN_STORAGE_KEY = "btsp.access_token";
const REFRESH_TOKEN_STORAGE_KEY = "btsp.refresh_token";
const inFlightGetRequests = new Map<string, Promise<unknown>>();
let inFlightRefresh: Promise<LoginResponse> | null = null;

export type LoginResponse = {
  access_token: string;
  refresh_token?: string | null;
  token_type: string;
};

export type CurrentUser = {
  email: string;
  display_name: string;
  roles: string[];
  permissions: string[];
  workflows: string[];
  vendor_code: string | null;
  active_vendor_code: string | null;
  vendor_accounts: Array<{
    vendor_code: string;
    name: string;
  }>;
  login_context: "standard" | "event";
  password_change_required: boolean;
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
  entity_code: string | null;
  vendor_code: string | null;
  vendor_codes: string[];
  is_active: boolean;
  password_change_required: boolean;
  roles: string[];
  permissions: string[];
};

export type AdminUserCreate = {
  email: string;
  display_name: string;
  password: string;
  home_store_number?: string | null;
  region_code?: string | null;
  entity_code?: string | null;
  vendor_code?: string | null;
  vendor_codes?: string[];
  is_active: boolean;
  password_change_required?: boolean;
  role_codes: string[];
};

export type AdminUserUpdate = {
  display_name?: string;
  password?: string;
  home_store_number?: string | null;
  region_code?: string | null;
  entity_code?: string | null;
  vendor_code?: string | null;
  vendor_codes?: string[];
  is_active?: boolean;
  password_change_required?: boolean;
  role_codes?: string[];
};

export type InternalMessage = {
  id: number;
  conversation_id: string;
  sender_email: string;
  recipient_email: string;
  subject: string;
  body: string;
  read_at: string | null;
  created_at: string;
};

export type MessageRecipient = {
  email: string;
  display_name: string;
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
    threshold: number | null;
    severity: "info" | "warning" | "critical";
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
    const sessionToken = window.sessionStorage.getItem(TOKEN_STORAGE_KEY);
    if (sessionToken) return sessionToken;
    const legacyToken = window.localStorage.getItem(TOKEN_STORAGE_KEY);
    if (!legacyToken) return null;
    window.sessionStorage.setItem(TOKEN_STORAGE_KEY, legacyToken);
    window.localStorage.removeItem(TOKEN_STORAGE_KEY);
    return legacyToken;
  } catch {
    return null;
  }
}

export function storeToken(token: string): void {
  try {
    window.sessionStorage.setItem(TOKEN_STORAGE_KEY, token);
    window.localStorage.removeItem(TOKEN_STORAGE_KEY);
  } catch {
    throw new Error(
      "Browser storage is unavailable; enable site storage to sign in",
    );
  }
}

export function storeRefreshToken(token: string | null | undefined): void {
  if (!token) return;
  try {
    window.sessionStorage.setItem(REFRESH_TOKEN_STORAGE_KEY, token);
    window.localStorage.removeItem(REFRESH_TOKEN_STORAGE_KEY);
  } catch {
    throw new Error(
      "Browser storage is unavailable; enable site storage to sign in",
    );
  }
}

export function getStoredRefreshToken(): string | null {
  if (typeof window === "undefined") return null;
  try {
    return (
      window.sessionStorage.getItem(REFRESH_TOKEN_STORAGE_KEY) ??
      window.localStorage.getItem(REFRESH_TOKEN_STORAGE_KEY)
    );
  } catch {
    return null;
  }
}

export function clearToken(): void {
  try {
    window.sessionStorage.removeItem(TOKEN_STORAGE_KEY);
    window.localStorage.removeItem(TOKEN_STORAGE_KEY);
    window.sessionStorage.removeItem(REFRESH_TOKEN_STORAGE_KEY);
    window.localStorage.removeItem(REFRESH_TOKEN_STORAGE_KEY);
  } catch {
    // Storage may be blocked by browser privacy settings. There is no token to clear in that case.
  }
}

export async function apiFetch<T>(
  path: string,
  options: RequestInit = {},
  allowRefresh = true,
): Promise<T> {
  const method = (options.method ?? "GET").toUpperCase();
  const canCoalesce =
    method === "GET" &&
    options.body === undefined &&
    options.headers === undefined &&
    options.signal === undefined;
  if (!canCoalesce) {
    return apiFetchOnce<T>(path, options, allowRefresh);
  }

  const requestKey = `${getStoredToken() ?? "anonymous"}:${path}`;
  const existing = inFlightGetRequests.get(requestKey);
  if (existing) return existing as Promise<T>;

  const request = apiFetchOnce<T>(path, options, allowRefresh).finally(() => {
    if (inFlightGetRequests.get(requestKey) === request) {
      inFlightGetRequests.delete(requestKey);
    }
  });
  inFlightGetRequests.set(requestKey, request);
  return request;
}

async function apiFetchOnce<T>(
  path: string,
  options: RequestInit,
  allowRefresh: boolean,
): Promise<T> {
  const token = getStoredToken();
  const usesFormData =
    typeof FormData !== "undefined" && options.body instanceof FormData;
  const response = await fetch(`${getApiBaseUrl()}/api/v1${path}`, {
    ...options,
    headers: {
      ...(!usesFormData ? { "Content-Type": "application/json" } : {}),
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options.headers,
    },
  });

  if (response.status === 401 && allowRefresh && getStoredRefreshToken()) {
    try {
      const refreshed = await refreshAccessToken();
      storeToken(refreshed.access_token);
      storeRefreshToken(refreshed.refresh_token);
      return apiFetch<T>(path, options, false);
    } catch {
      clearToken();
    }
  }
  if (!response.ok) throw new Error(await apiErrorMessage(response));
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

async function refreshAccessToken(): Promise<LoginResponse> {
  if (inFlightRefresh) return inFlightRefresh;
  const request = performRefreshAccessToken().finally(() => {
    if (inFlightRefresh === request) inFlightRefresh = null;
  });
  inFlightRefresh = request;
  return request;
}

async function performRefreshAccessToken(): Promise<LoginResponse> {
  const refreshToken = getStoredRefreshToken();
  if (!refreshToken) throw new Error("No refresh token available");
  const response = await fetch(`${getApiBaseUrl()}/api/v1/auth/refresh`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh_token: refreshToken }),
  });
  if (!response.ok) throw new Error("Refresh session expired");
  return response.json() as Promise<LoginResponse>;
}

export async function apiDownload(path: string): Promise<Blob> {
  return (await apiDownloadWithFilename(path)).blob;
}

export async function apiDownloadWithFilename(
  path: string,
): Promise<{ blob: Blob; filename: string | null }> {
  const token = getStoredToken();
  const response = await fetch(`${getApiBaseUrl()}/api/v1${path}`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });
  if (!response.ok)
    throw new Error(await apiErrorMessage(response, "download"));
  return {
    blob: await response.blob(),
    filename: filenameFromContentDisposition(
      response.headers.get("content-disposition"),
    ),
  };
}

async function apiErrorMessage(
  response: Response,
  operation: "request" | "download" = "request",
) {
  const fallback = `BTSP API ${operation} failed with status ${response.status}`;
  const contentType = response.headers.get("content-type") ?? "";
  if (contentType.includes("application/json")) {
    const payload = (await response.json().catch(() => null)) as {
      detail?: unknown;
      message?: unknown;
    } | null;
    const detail = payload?.detail ?? payload?.message;
    if (typeof detail === "string" && detail.trim()) return detail;
    if (Array.isArray(detail)) {
      const messages = detail
        .map((item) => {
          if (!item || typeof item !== "object") return null;
          const error = item as { loc?: unknown[]; msg?: unknown };
          const location = Array.isArray(error.loc)
            ? error.loc.slice(1).join(" → ")
            : "";
          const message =
            typeof error.msg === "string" ? error.msg : "Invalid value";
          return location ? `${location}: ${message}` : message;
        })
        .filter(Boolean);
      if (messages.length) return messages.join("; ");
    }
    return fallback;
  }
  const text = await response.text().catch(() => "");
  return text.trim() || fallback;
}

function filenameFromContentDisposition(value: string | null) {
  if (!value) return null;
  const encoded = value.match(/filename\*=UTF-8''([^;]+)/i)?.[1];
  if (encoded) {
    try {
      return sanitizeDownloadFilename(decodeURIComponent(encoded));
    } catch {
      return sanitizeDownloadFilename(encoded);
    }
  }
  const quoted = value.match(/filename="([^"]+)"/i)?.[1];
  if (quoted) return sanitizeDownloadFilename(quoted);
  const plain = value.match(/filename=([^;]+)/i)?.[1];
  return plain ? sanitizeDownloadFilename(plain) : null;
}

export function sanitizeDownloadFilename(value: string) {
  const cleaned = value
    .replace(/[/\\?%*:|"<>]/g, "-")
    .replace(/\s+/g, " ")
    .trim();
  return cleaned || null;
}

export async function login(
  email: string,
  password: string,
  loginContext: "standard" | "event" = "standard",
): Promise<LoginResponse> {
  return apiFetch<LoginResponse>("/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password, login_context: loginContext }),
  });
}

export async function getCurrentUser(): Promise<CurrentUser> {
  return apiFetch<CurrentUser>("/auth/me");
}

export async function selectVendorContext(
  vendorCode: string,
): Promise<LoginResponse> {
  return apiFetch<LoginResponse>("/auth/vendor-context", {
    method: "POST",
    body: JSON.stringify({ vendor_code: vendorCode }),
  });
}

export async function selectEventVendorContext(
  eventId: string,
  vendorCode: string,
): Promise<LoginResponse> {
  return apiFetch<LoginResponse>("/auth/event-vendor-context", {
    method: "POST",
    body: JSON.stringify({ event_id: eventId, vendor_code: vendorCode }),
  });
}

export async function changePassword(
  currentPassword: string,
  newPassword: string,
): Promise<void> {
  await apiFetch<void>("/auth/change-password", {
    method: "POST",
    body: JSON.stringify({
      current_password: currentPassword,
      new_password: newPassword,
    }),
  });
}

export async function requestPasswordReset(
  email: string,
): Promise<{ message: string; reset_token?: string | null }> {
  return apiFetch<{ message: string; reset_token?: string | null }>(
    "/auth/password-reset/request",
    {
      method: "POST",
      body: JSON.stringify({ email }),
    },
  );
}

export async function confirmPasswordReset(
  token: string,
  newPassword: string,
): Promise<void> {
  await apiFetch<void>("/auth/password-reset/confirm", {
    method: "POST",
    body: JSON.stringify({ token, new_password: newPassword }),
  });
}

export async function getAvailableWorkflows(): Promise<AvailableWorkflow[]> {
  return apiFetch<AvailableWorkflow[]>("/workflows/available");
}

export async function listMessageRecipients(): Promise<MessageRecipient[]> {
  return apiFetch<MessageRecipient[]>("/communications/recipients");
}

export async function listInternalMessages(): Promise<InternalMessage[]> {
  return apiFetch<InternalMessage[]>("/communications/messages");
}

export async function sendInternalMessage(payload: {
  recipient_email: string;
  subject: string;
  body: string;
  reply_to_message_id?: number;
}): Promise<InternalMessage> {
  return apiFetch<InternalMessage>("/communications/messages", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function markInternalMessageRead(
  messageId: number,
): Promise<InternalMessage> {
  return apiFetch<InternalMessage>(
    `/communications/messages/${messageId}/read`,
    {
      method: "POST",
    },
  );
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

export async function deleteAdminUser(email: string): Promise<void> {
  return apiFetch<void>(`/users/${encodeURIComponent(email)}`, {
    method: "DELETE",
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
