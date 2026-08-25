import { getApiBaseUrl } from "./api-origin";

const TOKEN_STORAGE_KEY = "btsp.access_token";
const REFRESH_TOKEN_STORAGE_KEY = "btsp.refresh_token";

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

async function refreshAccessToken(): Promise<{
  access_token: string;
  refresh_token?: string | null;
}> {
  const refreshToken = getStoredRefreshToken();
  if (!refreshToken) throw new Error("No refresh token available");
  const response = await fetch(`${getApiBaseUrl()}/api/v1/auth/refresh`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh_token: refreshToken }),
  });
  if (!response.ok) throw new Error("Refresh session expired");
  return response.json() as Promise<{
    access_token: string;
    refresh_token?: string | null;
  }>;
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
