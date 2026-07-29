"use client";

import { useCallback, useEffect, useState } from "react";
import {
  EventPoll,
  getActiveEventPoll,
  voteInEventPoll,
} from "@/lib/event-poll-api";
import { subscribeEventRealtime } from "@/lib/event-realtime";

export function EventLivePoll({ subEventId }: { subEventId: string }) {
  const [poll, setPoll] = useState<EventPoll | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const refresh = useCallback(
    () => getActiveEventPoll(subEventId).then(setPoll),
    [subEventId],
  );

  useEffect(() => {
    void refresh();
    const timer = window.setInterval(() => void refresh(), 15_000);
    const unsubscribe = subscribeEventRealtime(
      subEventId,
      () => void refresh(),
    );
    return () => {
      window.clearInterval(timer);
      unsubscribe();
    };
  }, [refresh, subEventId]);

  if (!poll) return null;
  const voted = Boolean(poll.selected_option_id);
  return (
    <section className="event-ui mb-5 rounded-2xl border-2 border-blue-200 bg-blue-50 p-5">
      <p className="brand-eyebrow">Live poll</p>
      <h2 className="text-xl font-bold">{poll.question}</h2>
      {error ? <p className="mt-2 text-sm text-red-700">{error}</p> : null}
      <div className="mt-4 grid gap-2">
        {poll.options.map((option) => (
          <button
            className={`event-selectable relative overflow-hidden rounded-xl border p-3 text-left font-semibold ${poll.selected_option_id === option.id ? "is-selected ring-2 ring-blue-200" : ""}`}
            disabled={busy || voted}
            key={option.id}
            onClick={() => {
              setBusy(true);
              setError(null);
              void voteInEventPoll(poll.id, option.id)
                .then(setPoll)
                .catch((caught: unknown) =>
                  setError(
                    caught instanceof Error
                      ? caught.message
                      : "Vote could not be recorded",
                  ),
                )
                .finally(() => setBusy(false));
            }}
            type="button"
          >
            <span
              className="absolute inset-y-0 left-0 bg-blue-100 opacity-50"
              style={{ width: `${option.percentage}%` }}
            />
            <span className="relative flex justify-between gap-3">
              <span>{option.label}</span>
              {poll.show_results || voted ? (
                <span>{option.percentage.toFixed(0)}%</span>
              ) : null}
            </span>
          </button>
        ))}
      </div>
      <p className="mt-3 text-sm text-slate-600">
        {voted ? "Your vote is recorded." : "Choose one response."}
        {poll.show_results ? ` · ${poll.total_votes} votes` : ""}
      </p>
    </section>
  );
}
