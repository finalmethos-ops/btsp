"use client";

import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { EventAccessUnavailable } from "@/components/EventAccessUnavailable";
import { EventPresenterMonitor } from "@/components/EventPresenterMonitor";

export default function EventPresenterMonitorPage() {
  const params = useParams<{ subEventId: string }>();
  const [presenterToken, setPresenterToken] = useState<string | null>();

  useEffect(() => {
    const fragment = new URLSearchParams(window.location.hash.slice(1));
    const storageKey = `btsp.presenter.${params.subEventId}`;
    const fragmentToken = fragment.get("presenter_token");
    try {
      if (fragmentToken)
        window.sessionStorage.setItem(storageKey, fragmentToken);
      setPresenterToken(
        fragmentToken ?? window.sessionStorage.getItem(storageKey),
      );
    } catch {
      setPresenterToken(fragmentToken);
    }
    if (fragmentToken)
      window.history.replaceState(
        null,
        "",
        `${window.location.pathname}${window.location.search}`,
      );
  }, [params.subEventId]);

  if (presenterToken === undefined)
    return <main className="loading-screen">Opening presenter monitor…</main>;

  if (!presenterToken)
    return (
      <EventAccessUnavailable
        message="Open a fresh presenter-monitor link from the live presentation control panel."
        title="Presenter link required"
      />
    );

  return (
    <EventPresenterMonitor
      presenterToken={presenterToken}
      subEventId={params.subEventId}
    />
  );
}
