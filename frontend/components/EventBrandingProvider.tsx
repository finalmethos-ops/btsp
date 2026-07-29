"use client";

import {
  createContext,
  CSSProperties,
  ReactNode,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";
import {
  downloadEventBranding,
  listMyEvents,
  ManagedEvent,
} from "@/lib/event-admin-api";
import { useAuth } from "@/lib/auth";

type EventBrandStyle = CSSProperties & {
  "--event-brand-image"?: string;
  "--event-theme-primary"?: string;
  "--event-theme-accent"?: string;
  "--event-theme-primary-text"?: string;
  "--event-theme-accent-text"?: string;
};

type EventBrandingContextValue = {
  eventById: Record<string, ManagedEvent>;
  brandingByEventId: Record<string, string>;
  brandedClassName: (eventId: string, baseClassName?: string) => string;
  brandedStyle: (eventId: string) => EventBrandStyle | undefined;
};

const EventBrandingContext = createContext<EventBrandingContextValue>({
  eventById: {},
  brandingByEventId: {},
  brandedClassName: (_eventId, baseClassName = "") => baseClassName,
  brandedStyle: () => undefined,
});

function eventThemeStyle(
  event: ManagedEvent | undefined,
  brandingUrl?: string | null,
): EventBrandStyle | undefined {
  if (!event && !brandingUrl) return undefined;
  const primary = event?.theme_primary_color ?? "#07142c";
  const accent = event?.theme_accent_color ?? "#ffd400";
  return {
    "--event-brand-image": brandingUrl ? `url(${brandingUrl})` : undefined,
    "--event-theme-primary": primary,
    "--event-theme-accent": accent,
    // Keep text legible even when an event uses a darker-than-default accent.
    "--event-theme-primary-text": readableTextColor(primary),
    "--event-theme-accent-text": readableTextColor(accent),
  };
}

function readableTextColor(color: string) {
  const match = color.trim().match(/^#([0-9a-f]{6})$/i);
  if (!match) return "#07142c";
  const channels = [0, 2, 4].map(
    (offset) => Number.parseInt(match[1].slice(offset, offset + 2), 16) / 255,
  );
  const luminance = channels
    .map((channel) =>
      channel <= 0.03928 ? channel / 12.92 : ((channel + 0.055) / 1.055) ** 2.4,
    )
    .reduce(
      (sum, channel, index) => sum + channel * [0.2126, 0.7152, 0.0722][index],
      0,
    );
  return luminance > 0.42 ? "#07142c" : "#f8fbff";
}

export function EventBrandingProvider({ children }: { children: ReactNode }) {
  const { user } = useAuth();
  const [events, setEvents] = useState<ManagedEvent[]>([]);
  const [brandingByEventId, setBrandingByEventId] = useState<
    Record<string, string>
  >({});
  // Branding must also load for administrators while they are working inside
  // the event portal.  Their platform permissions should not disable the
  // event-scoped theme or logo.
  const shouldLoad = Boolean(user && user.login_context === "event");

  useEffect(() => {
    if (!shouldLoad) {
      setEvents([]);
      setBrandingByEventId({});
      return;
    }
    let active = true;
    const objectUrls: string[] = [];

    async function load() {
      const assignedEvents = await listMyEvents();
      if (!active) return;
      setEvents(assignedEvents);
      const brandedEvents = assignedEvents.filter(
        (event) => event.has_branding,
      );
      const entries = await Promise.all(
        brandedEvents.map(async (event) => {
          try {
            const blob = await downloadEventBranding(event.id);
            const url = URL.createObjectURL(blob);
            objectUrls.push(url);
            return [event.id, url] as const;
          } catch {
            return null;
          }
        }),
      );
      if (active) {
        setBrandingByEventId(
          Object.fromEntries(entries.filter((entry) => entry !== null)),
        );
      }
    }

    void load().catch(() => undefined);
    return () => {
      active = false;
      objectUrls.forEach((url) => URL.revokeObjectURL(url));
    };
  }, [shouldLoad]);

  const value = useMemo<EventBrandingContextValue>(() => {
    const eventById = Object.fromEntries(
      events.map((event) => [event.id, event]),
    );
    return {
      eventById,
      brandingByEventId,
      brandedClassName(eventId, baseClassName = "") {
        return [
          baseClassName,
          "event-branded-surface",
          eventById[eventId] ? "has-event-theme" : "",
          brandingByEventId[eventId] ? "has-event-branding-image" : "",
        ]
          .filter(Boolean)
          .join(" ");
      },
      brandedStyle(eventId) {
        return eventThemeStyle(eventById[eventId], brandingByEventId[eventId]);
      },
    };
  }, [brandingByEventId, events]);

  return (
    <EventBrandingContext.Provider value={value}>
      {children}
    </EventBrandingContext.Provider>
  );
}

export function useEventBranding() {
  return useContext(EventBrandingContext);
}

export function useEventBrandAsset(eventId: string | null | undefined) {
  const context = useEventBranding();
  const [brandingUrl, setBrandingUrl] = useState<string | null>(null);
  const contextBrandingUrl = eventId
    ? context.brandingByEventId[eventId]
    : null;

  useEffect(() => {
    if (!eventId || contextBrandingUrl) {
      setBrandingUrl(null);
      return;
    }
    let active = true;
    let objectUrl: string | null = null;
    void downloadEventBranding(eventId)
      .then((blob) => {
        objectUrl = URL.createObjectURL(blob);
        if (active) setBrandingUrl(objectUrl);
      })
      .catch(() => {
        if (active) setBrandingUrl(null);
      });
    return () => {
      active = false;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [contextBrandingUrl, eventId]);

  const resolvedUrl = contextBrandingUrl ?? brandingUrl;
  const event = eventId ? context.eventById[eventId] : undefined;
  return {
    brandingUrl: resolvedUrl,
    brandedClassName(baseClassName = "") {
      return [
        baseClassName,
        "event-branded-surface",
        event || resolvedUrl ? "has-event-theme" : "",
        resolvedUrl ? "has-event-branding-image" : "",
      ]
        .filter(Boolean)
        .join(" ");
    },
    brandedStyle(): EventBrandStyle | undefined {
      return eventThemeStyle(event, resolvedUrl);
    },
  };
}
