export function getApiBaseUrl(): string {
  const configured = process.env.NEXT_PUBLIC_API_BASE_URL;
  if (configured) return configured;
  if (typeof window !== "undefined" && window.location.port === "3000") {
    return `${window.location.protocol}//${window.location.hostname}:8000`;
  }
  return "";
}
