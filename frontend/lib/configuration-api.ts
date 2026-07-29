import { getStoredToken } from "./api";

import { getApiBaseUrl } from "./api-origin";

export type ConfigEntry = {
  id: number;
  scope_type: string;
  scope_key: string;
  key: string;
  value: Record<string, unknown>;
  description: string | null;
  is_active: boolean;
  updated_by: string;
  created_at: string;
  updated_at: string;
};

export type ConfigEntryWrite = {
  scope_type: string;
  scope_key: string;
  key: string;
  value: Record<string, unknown>;
  description?: string | null;
  is_active: boolean;
  updated_by: string;
};

export type ConfigurationChange = {
  id: string;
  scope_type: string;
  scope_key: string;
  key: string;
  proposed_value: Record<string, unknown>;
  description: string | null;
  status: "pending" | "approved" | "rejected";
  requested_by: string;
  decided_by: string | null;
  decision_note: string | null;
  created_at: string;
  decided_at: string | null;
};

async function configFetch<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const token = getStoredToken();
  const response = await fetch(`${getApiBaseUrl()}/api/v1${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options.headers,
    },
  });

  if (!response.ok) {
    throw new Error(
      `BTSP configuration request failed with status ${response.status}`,
    );
  }

  return response.json() as Promise<T>;
}

export async function listConfigEntries(
  scopeType?: string,
  scopeKey?: string,
): Promise<ConfigEntry[]> {
  const params = new URLSearchParams();
  if (scopeType) {
    params.set("scope_type", scopeType);
  }
  if (scopeKey) {
    params.set("scope_key", scopeKey);
  }
  const query = params.toString();
  return configFetch<ConfigEntry[]>(
    `/configuration${query ? `?${query}` : ""}`,
  );
}

export async function saveConfigEntry(
  payload: ConfigEntryWrite,
): Promise<ConfigEntry> {
  return configFetch<ConfigEntry>("/configuration", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function seedConfigDefaults(): Promise<{ seeded_count: number }> {
  return configFetch<{ seeded_count: number }>("/configuration/seed-defaults", {
    method: "POST",
  });
}

export async function listConfigurationChanges(
  status?: string,
): Promise<ConfigurationChange[]> {
  return configFetch<ConfigurationChange[]>(
    `/configuration/changes${status ? `?status_filter=${encodeURIComponent(status)}` : ""}`,
  );
}

export async function requestConfigurationChange(payload: {
  scope_type: string;
  scope_key: string;
  key: string;
  proposed_value: Record<string, unknown>;
  description?: string | null;
}): Promise<ConfigurationChange> {
  return configFetch<ConfigurationChange>("/configuration/changes", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function decideConfigurationChange(
  id: string,
  decision: "approve" | "reject",
  note?: string,
): Promise<ConfigurationChange> {
  return configFetch<ConfigurationChange>(
    `/configuration/changes/${id}/${decision}`,
    { method: "POST", body: JSON.stringify({ note }) },
  );
}
