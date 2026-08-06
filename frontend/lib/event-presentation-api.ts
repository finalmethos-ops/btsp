import { apiDownload, apiFetch } from "./api";
import { getApiBaseUrl } from "./api-origin";
import { EventProductSlide } from "./event-product-slide-api";

export type EventPresentation = {
  sub_event_id: string;
  event_id: string;
  event_name: string;
  event_theme_primary_color: string;
  event_theme_accent_color: string;
  event_has_branding: boolean;
  sub_event_name: string;
  status: "idle" | "live" | "ended";
  ordering_status: "open" | "closed";
  ordering_opened_at: string | null;
  current_slide: EventProductSlide | null;
  total_slides: number;
  current_position: number | null;
  total_units_ordered: number;
  total_combined_spend: string;
  variant_units_ordered: Record<string, number>;
  sub_event_units_ordered: number;
  sub_event_combined_spend: string;
  presenter_notes: string | null;
  slide_queue: Array<{
    id: string;
    position: number;
    slide_type: "product" | "filler";
    filler_category:
      | "trivia"
      | "giveaway"
      | "sponsorship"
      | "special_thanks"
      | "raffle"
      | null;
    model_number: string | null;
    name: string;
    presenter_notes: string | null;
  }>;
  presenter_slides: EventProductSlide[];
  updated_at: string | null;
};

export type PresentationAction =
  | "start"
  | "previous"
  | "next"
  | "open"
  | "close"
  | "end";

export type EventLiveAnalytics = {
  sub_event_id: string;
  current_slide_id: string | null;
  assigned_entities: number;
  responding_entities: number;
  confirmed_entities: number;
  waitlisted_entities: number;
  entities_remaining: number;
  confirmed_units: number;
  confirmed_spend: string;
  waitlisted_units: number;
  orders: Array<{
    entity_code: string;
    quantity: number;
    total_cost: string;
    status: string;
    updated_at: string;
  }>;
};

export const getEventPresentation = (subEventId: string) =>
  apiFetch<EventPresentation>(`/event-presentations/${subEventId}`);

export const getEventPresenterPresentation = (subEventId: string) =>
  apiFetch<EventPresentation>(`/event-presentations/${subEventId}/presenter`);

export type EventProjectorAccess = {
  projector_token: string;
  expires_at: string;
};

export type EventPresenterAccess = {
  presenter_token: string;
  expires_at: string;
};

export const createEventProjectorAccess = (subEventId: string) =>
  apiFetch<EventProjectorAccess>(
    `/event-presentations/${subEventId}/projector-access`,
    { method: "POST" },
  );

export const createEventPresenterAccess = (subEventId: string) =>
  apiFetch<EventPresenterAccess>(
    `/event-presentations/${subEventId}/presenter-access`,
    { method: "POST" },
  );

export const controlEventPresentation = (
  subEventId: string,
  action: PresentationAction,
) =>
  apiFetch<EventPresentation>(`/event-presentations/${subEventId}/control`, {
    method: "POST",
    body: JSON.stringify({ action }),
  });

export const downloadPresentationImage = (slideId: string) =>
  apiDownload(`/event-product-slides/${slideId}/image`);

export const getEventLiveAnalytics = (subEventId: string) =>
  apiFetch<EventLiveAnalytics>(`/event-presentations/${subEventId}/analytics`);

async function projectorRequest(
  path: string,
  projectorToken: string,
): Promise<Response> {
  const response = await fetch(`${getApiBaseUrl()}/api/v1${path}`, {
    headers: { "X-BTSP-Projector-Token": projectorToken },
  });
  if (!response.ok) {
    const payload = (await response.json().catch(() => null)) as {
      detail?: unknown;
    } | null;
    throw new Error(
      typeof payload?.detail === "string"
        ? payload.detail
        : `Projector request failed with status ${response.status}`,
    );
  }
  return response;
}

async function presenterRequest(
  path: string,
  presenterToken: string,
): Promise<Response> {
  const response = await fetch(`${getApiBaseUrl()}/api/v1${path}`, {
    headers: { "X-BTSP-Presenter-Token": presenterToken },
  });
  if (!response.ok) {
    const payload = (await response.json().catch(() => null)) as {
      detail?: unknown;
    } | null;
    throw new Error(
      typeof payload?.detail === "string"
        ? payload.detail
        : `Presenter request failed with status ${response.status}`,
    );
  }
  return response;
}

export async function getPublicEventPresentation(
  subEventId: string,
  projectorToken: string,
) {
  const response = await projectorRequest(
    `/public-event-presentations/${subEventId}`,
    projectorToken,
  );
  return response.json() as Promise<EventPresentation>;
}

export async function downloadPublicPresentationImage(
  subEventId: string,
  slideId: string,
  projectorToken: string,
) {
  const response = await projectorRequest(
    `/public-event-presentations/${subEventId}/slides/${slideId}/image`,
    projectorToken,
  );
  return response.blob();
}

export async function downloadPublicPresentationBranding(
  subEventId: string,
  projectorToken: string,
) {
  const response = await projectorRequest(
    `/public-event-presentations/${subEventId}/branding`,
    projectorToken,
  );
  return response.blob();
}

export async function getPublicEventPresenterPresentation(
  subEventId: string,
  presenterToken: string,
) {
  const response = await presenterRequest(
    `/public-event-presentations/${subEventId}/presenter-monitor`,
    presenterToken,
  );
  return response.json() as Promise<EventPresentation>;
}

export async function downloadPublicPresenterImage(
  subEventId: string,
  slideId: string,
  presenterToken: string,
) {
  const response = await presenterRequest(
    `/public-event-presentations/${subEventId}/presenter-monitor/slides/${slideId}/image`,
    presenterToken,
  );
  return response.blob();
}
