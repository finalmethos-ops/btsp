import { apiFetch } from "./api";

export type EventFillerCategory =
  | "trivia"
  | "giveaway"
  | "sponsorship"
  | "special_thanks"
  | "raffle"
  | "full_screen_image";

export type EventProductSlide = {
  id: string;
  event_id: string;
  sub_event_id: string;
  position: number;
  slide_type: "product" | "filler";
  filler_category: EventFillerCategory | null;
  vendor_name: string | null;
  category: string | null;
  catalog_product_code: string | null;
  model_number: string | null;
  name: string;
  vendor_code: string | null;
  description: string | null;
  specifications: string | null;
  event_unit_cost: string | null;
  standard_cost: string | null;
  currency: string;
  minimum_order_quantity: number;
  available_inventory: number | null;
  max_event_units: number | null;
  allow_waitlist: boolean;
  delivery_window_start: string | null;
  delivery_window_end: string | null;
  vendor_delivery_notes: string | null;
  presenter_notes: string | null;
  product_variants: Array<{
    model_number: string;
    name: string;
    event_unit_cost: string;
    standard_cost: string | null;
    minimum_order_quantity: number;
  }>;
  status: "draft" | "ready" | "archived";
  has_image: boolean;
  created_by: string;
  created_at: string;
};

export type EventProductSlideWrite = Omit<
  EventProductSlide,
  | "id"
  | "event_id"
  | "sub_event_id"
  | "position"
  | "vendor_name"
  | "has_image"
  | "created_by"
  | "created_at"
>;

export const listEventProductSlides = (subEventId: string) =>
  apiFetch<EventProductSlide[]>(
    `/event-product-slides/sub-events/${subEventId}`,
  );

export const createEventProductSlide = (
  subEventId: string,
  payload: EventProductSlideWrite,
) =>
  apiFetch<EventProductSlide>(
    `/event-product-slides/sub-events/${subEventId}`,
    {
      method: "POST",
      body: JSON.stringify(payload),
    },
  );

export const updateEventProductSlide = (
  slideId: string,
  payload: EventProductSlideWrite,
) =>
  apiFetch<EventProductSlide>(`/event-product-slides/${slideId}`, {
    method: "PUT",
    body: JSON.stringify(payload),
  });

export const deleteEventProductSlide = (slideId: string) =>
  apiFetch<void>(`/event-product-slides/${slideId}`, { method: "DELETE" });

export const reorderEventProductSlides = (
  subEventId: string,
  slideIds: string[],
) =>
  apiFetch<EventProductSlide[]>(
    `/event-product-slides/sub-events/${subEventId}/order`,
    { method: "PUT", body: JSON.stringify({ slide_ids: slideIds }) },
  );

export const uploadEventProductImage = (slideId: string, file: File) => {
  const body = new FormData();
  body.append("file", file);
  return apiFetch<EventProductSlide>(`/event-product-slides/${slideId}/image`, {
    method: "POST",
    body,
  });
};

export type EventProductWebFill = {
  model_number: string;
  title: string;
  summary: string;
  source_url: string;
  image_url: string | null;
};

export const webFillEventProduct = (
  modelNumber: string,
  productName: string,
) => {
  const params = new URLSearchParams({ model_number: modelNumber });
  if (productName) params.set("product_name", productName);
  return apiFetch<EventProductWebFill>(
    `/event-product-slides/web-fill?${params}`,
  );
};

export const importEventProductImage = (slideId: string, imageUrl: string) =>
  apiFetch<EventProductSlide>(
    `/event-product-slides/${slideId}/image-from-web`,
    {
      method: "POST",
      body: JSON.stringify({ image_url: imageUrl }),
    },
  );
