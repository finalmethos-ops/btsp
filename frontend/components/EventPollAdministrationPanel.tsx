"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
import { ManagedSubEvent } from "@/lib/event-admin-api";
import {
  createEventPoll,
  EventPoll,
  listEventPolls,
  setEventPollStatus,
} from "@/lib/event-poll-api";
import { subscribeEventRealtime } from "@/lib/event-realtime";

export function EventPollAdministrationPanel({
  subEvents,
}: {
  subEvents: ManagedSubEvent[];
}) {
  const [subEventId, setSubEventId] = useState(subEvents[0]?.id ?? "");
  const [polls, setPolls] = useState<EventPoll[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(() => {
    if (!subEventId) return Promise.resolve();
    return listEventPolls(subEventId).then(setPolls);
  }, [subEventId]);

  useEffect(() => {
    void refresh().catch((caught: unknown) =>
      setError(
        caught instanceof Error ? caught.message : "Unable to load polls.",
      ),
    );
    if (!subEventId) return;
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

  async function create(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const data = new FormData(form);
    const options = String(data.get("options"))
      .split("\n")
      .map((value) => value.trim())
      .filter(Boolean);
    setBusy(true);
    setError(null);
    try {
      await createEventPoll(subEventId, {
        question: String(data.get("question")),
        options,
        show_results: data.get("show_results") === "on",
      });
      form.reset();
      await refresh();
    } catch (caught) {
      setError(
        caught instanceof Error ? caught.message : "Unable to create the poll.",
      );
    } finally {
      setBusy(false);
    }
  }

  async function changeStatus(poll: EventPoll, status: "open" | "closed") {
    setBusy(true);
    setError(null);
    try {
      await setEventPollStatus(poll.id, status);
      await refresh();
    } catch (caught) {
      setError(
        caught instanceof Error ? caught.message : "Unable to update the poll.",
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="event-ui rounded-2xl border bg-white p-5">
      <p className="brand-eyebrow">Live engagement</p>
      <h3 className="text-xl font-bold">Polls and product voting</h3>
      {!subEvents.length ? (
        <p className="mt-3 text-sm text-slate-500">
          Add a sub-event before creating a poll.
        </p>
      ) : (
        <>
          <label className="mt-4 block text-sm font-semibold">
            Sub-event
            <select
              className="mt-1 w-full rounded-lg border p-3"
              onChange={(event) => setSubEventId(event.target.value)}
              value={subEventId}
            >
              {subEvents.map((item) => (
                <option key={item.id} value={item.id}>
                  {item.name}
                </option>
              ))}
            </select>
          </label>
          {error ? (
            <p className="mt-3 rounded-lg bg-red-50 p-3 text-red-800">
              {error}
            </p>
          ) : null}
          <form
            className="mt-4 grid gap-3 rounded-xl bg-slate-50 p-4"
            onSubmit={create}
          >
            <label className="font-semibold">
              Question
              <input
                className="mt-1 w-full rounded-lg border bg-white p-3"
                name="question"
                required
              />
            </label>
            <label className="font-semibold">
              Choices (one per line)
              <textarea
                className="mt-1 min-h-28 w-full rounded-lg border bg-white p-3"
                name="options"
                placeholder={"Option one\nOption two"}
                required
              />
            </label>
            <label className="flex items-center gap-2 text-sm">
              <input defaultChecked name="show_results" type="checkbox" />
              Show live results to attendees
            </label>
            <button
              className="rounded-xl bg-blue-800 p-3 font-bold text-white disabled:bg-slate-400"
              disabled={busy}
            >
              Create poll
            </button>
          </form>
          <div className="mt-4 space-y-3">
            {polls.map((poll) => (
              <article className="rounded-xl border p-4" key={poll.id}>
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <span className="text-xs font-bold uppercase text-blue-700">
                      {poll.status}
                    </span>
                    <h4 className="font-bold">{poll.question}</h4>
                    <p className="text-sm text-slate-500">
                      {poll.total_votes} votes
                    </p>
                  </div>
                  {poll.status === "open" ? (
                    <button
                      className="rounded-lg border px-3 py-2 font-semibold"
                      disabled={busy}
                      onClick={() => void changeStatus(poll, "closed")}
                      type="button"
                    >
                      Close
                    </button>
                  ) : (
                    <button
                      className="rounded-lg bg-green-700 px-3 py-2 font-semibold text-white"
                      disabled={busy}
                      onClick={() => void changeStatus(poll, "open")}
                      type="button"
                    >
                      Open live
                    </button>
                  )}
                </div>
                <div className="mt-3 space-y-2">
                  {poll.options.map((option) => (
                    <div className="text-sm" key={option.id}>
                      <div className="flex justify-between">
                        <span>{option.label}</span>
                        <span>
                          {option.vote_count} · {option.percentage.toFixed(0)}%
                        </span>
                      </div>
                      <div className="mt-1 h-2 overflow-hidden rounded bg-slate-100">
                        <div
                          className="h-full bg-blue-700"
                          style={{ width: `${option.percentage}%` }}
                        />
                      </div>
                    </div>
                  ))}
                </div>
              </article>
            ))}
          </div>
        </>
      )}
    </section>
  );
}
