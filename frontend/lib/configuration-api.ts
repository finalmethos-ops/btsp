import { getStoredToken } from './api';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://localhost:8000';

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

async function configFetch<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = getStoredToken();
  const response = await fetch(`${API_BASE_URL}/api/v1${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options.headers,
    },
  });

  if (!response.ok) {
    throw new Error(`BTSP configuration request failed with status ${response.status}`);
  }

  return response.json() as Promise<T>;
}

export async function listConfigEntries(scopeType?: string, scopeKey?: string): Promise<ConfigEntry[]> {
  const params = new URLSearchParams();
  if (scopeType) {
    params.set('scope_type', scopeType);
  }
  if (scopeKey) {
    params.set('scope_key', scopeKey);
  }
  const query = params.toString();
  return configFetch<ConfigEntry[]>(`/configuration${query ? `?${query}` : ''}`);
}

export async function saveConfigEntry(payload: ConfigEntryWrite): Promise<ConfigEntry> {
  return configFetch<ConfigEntry>('/configuration', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export async function seedConfigDefaults(): Promise<{ seeded_count: number }> {
  return configFetch<{ seeded_count: number }>('/configuration/seed-defaults', {
    method: 'POST',
  });
}
