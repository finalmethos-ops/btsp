"use client";

import { createContext, ReactNode, useContext } from "react";

const EventScopeContext = createContext<string | null>(null);

export function EventScopeProvider({
  children,
  eventId,
}: {
  children: ReactNode;
  eventId: string;
}) {
  return (
    <EventScopeContext.Provider value={eventId}>
      {children}
    </EventScopeContext.Provider>
  );
}

export function useEventScope() {
  return useContext(EventScopeContext);
}
