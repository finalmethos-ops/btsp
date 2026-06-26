const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://localhost:8000';
const TOKEN_STORAGE_KEY = 'btsp.access_token';

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

export function getStoredToken(): string | null {
  if (typeof window === 'undefined') {
    return null;
  }
  return window.localStorage.getItem(TOKEN_STORAGE_KEY);
}

export function storeToken(token: string): void {
  window.localStorage.setItem(TOKEN_STORAGE_KEY, token);
}

export function clearToken(): void {
  window.localStorage.removeItem(TOKEN_STORAGE_KEY);
}

async function apiFetch<T>(path: string, options: RequestInit = {}): Promise<T> {
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
    throw new Error(`BTSP API request failed with status ${response.status}`);
  }

  return response.json() as Promise<T>;
}

export async function login(email: string, password: string): Promise<LoginResponse> {
  return apiFetch<LoginResponse>('/auth/login', {
    method: 'POST',
    body: JSON.stringify({ email, password }),
  });
}

export async function getCurrentUser(): Promise<CurrentUser> {
  return apiFetch<CurrentUser>('/auth/me');
}

export async function getAvailableWorkflows(): Promise<AvailableWorkflow[]> {
  return apiFetch<AvailableWorkflow[]>('/workflows/available');
}

export async function listAdminUsers(): Promise<AdminUser[]> {
  return apiFetch<AdminUser[]>('/users');
}

export async function createAdminUser(payload: AdminUserCreate): Promise<AdminUser> {
  return apiFetch<AdminUser>('/users', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export async function updateAdminUser(email: string, payload: AdminUserUpdate): Promise<AdminUser> {
  return apiFetch<AdminUser>(`/users/${encodeURIComponent(email)}`, {
    method: 'PATCH',
    body: JSON.stringify(payload),
  });
}
