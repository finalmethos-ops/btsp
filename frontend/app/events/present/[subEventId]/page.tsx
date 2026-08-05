"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { EventAccessUnavailable } from "@/components/EventAccessUnavailable";
import { EventPresentationDisplay } from "@/components/EventPresentationDisplay";

export default function EventPresentationPage() {
  const params = useParams<{ subEventId: string }>();
  const [projectorToken, setProjectorToken] = useState<string | null>();

  useEffect(() => {
    const fragment = new URLSearchParams(window.location.hash.slice(1));
    const storageKey = `btsp.projector.${params.subEventId}`;
    const fragmentToken = fragment.get("projector_token");
    try {
      if (fragmentToken)
        window.sessionStorage.setItem(storageKey, fragmentToken);
      setProjectorToken(
        fragmentToken ?? window.sessionStorage.getItem(storageKey),
      );
    } catch {
      setProjectorToken(fragmentToken);
    }
    if (fragmentToken)
      window.history.replaceState(
        null,
        "",
        `${window.location.pathname}${window.location.search}`,
      );
  }, [params.subEventId]);

  if (projectorToken === undefined)
    return <main className="loading-screen">Opening projector display…</main>;

  if (!projectorToken)
    return (
      <EventAccessUnavailable
        message="Open a fresh projector link from the live presentation control panel."
        title="Projector link required"
      />
    );

  return (
    <EventPresentationDisplay
      projectorToken={projectorToken}
      subEventId={params.subEventId}
    />
  );
}
