import { apiFetch } from "./api";
import { CatalogVendor } from "./purchasing-api";

export type EventVendorBoothStatus = "draft" | "published";

export type EventVendorBooth = {
  id: string;
  event_id: string;
  event_name: string;
  vendor_code: string;
  vendor_name: string | null;
  booth_name: string;
  booth_number: string | null;
  location: string | null;
  description: string | null;
  contact_name: string | null;
  contact_email: string | null;
  website_url: string | null;
  status: EventVendorBoothStatus;
  updated_at: string;
};

export type EventVendorBoothWrite = Omit<
  EventVendorBooth,
  "id" | "event_id" | "event_name" | "vendor_name" | "updated_at"
>;

export const listEventVendorBooths = (eventId: string) =>
  apiFetch<EventVendorBooth[]>(`/event-vendor-booths/${eventId}`);

export const listAvailableEventVendors = (eventId: string) =>
  apiFetch<CatalogVendor[]>(
    `/event-vendor-booths/${eventId}/available-vendors`,
  );

export const createEventOnlyVendor = (eventId: string, name: string) =>
  apiFetch<CatalogVendor>(
    `/event-vendor-booths/${eventId}/event-only-vendors`,
    {
      method: "POST",
      body: JSON.stringify({ name }),
    },
  );

export const listMyEventVendorBooths = () =>
  apiFetch<EventVendorBooth[]>("/event-vendor-booths/mine");

export const createEventVendorBooth = (
  eventId: string,
  payload: EventVendorBoothWrite,
) =>
  apiFetch<EventVendorBooth>(`/event-vendor-booths/${eventId}`, {
    method: "POST",
    body: JSON.stringify(payload),
  });

export const updateEventVendorBooth = (
  eventId: string,
  boothId: string,
  payload: EventVendorBoothWrite,
) =>
  apiFetch<EventVendorBooth>(`/event-vendor-booths/${eventId}/${boothId}`, {
    method: "PUT",
    body: JSON.stringify(payload),
  });

export const updateMyEventVendorBooth = (
  boothId: string,
  payload: EventVendorBoothWrite,
) =>
  apiFetch<EventVendorBooth>(`/event-vendor-booths/mine/${boothId}`, {
    method: "PUT",
    body: JSON.stringify(payload),
  });
