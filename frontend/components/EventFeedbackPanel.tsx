"use client";

import { FormEvent, useEffect, useState } from "react";
import {
  getEventFeedback,
  submitEventFeedback,
  EventFeedbackSummary,
} from "@/lib/event-feedback-api";

export function EventFeedbackPanel({ eventId }: { eventId: string }) {
  const [summary, setSummary] = useState<EventFeedbackSummary | null>(null);
  const [rating, setRating] = useState(5);
  const [comments, setComments] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  useEffect(() => {
    void getEventFeedback(eventId)
      .then(setSummary)
      .catch(() => undefined);
  }, [eventId]);
  async function submit(event: FormEvent) {
    event.preventDefault();
    setSummary(await submitEventFeedback(eventId, rating, comments));
    setMessage("Feedback saved.");
  }
  return (
    <section className="event-glass-pane rounded-2xl border p-5">
      <p className="brand-eyebrow">Post-event feedback</p>
      <h2 className="text-xl font-bold">How was your event experience?</h2>
      <form
        className="mt-4 grid gap-3 sm:grid-cols-[150px_1fr_auto]"
        onSubmit={(event) => void submit(event)}
      >
        <select
          aria-label="Rating"
          className="rounded-lg border p-2"
          onChange={(event) => setRating(Number(event.target.value))}
          value={rating}
        >
          {[5, 4, 3, 2, 1].map((value) => (
            <option key={value} value={value}>
              {value} / 5
            </option>
          ))}
        </select>
        <input
          aria-label="Comments"
          className="rounded-lg border p-2"
          onChange={(event) => setComments(event.target.value)}
          placeholder="Optional comments"
          value={comments}
        />
        <button
          className="rounded-lg bg-blue-800 px-4 py-2 font-bold text-white"
          type="submit"
        >
          Save feedback
        </button>
      </form>
      {message ? (
        <p className="mt-2 text-sm text-green-700">{message}</p>
      ) : null}
      {summary?.average_rating != null ? (
        <p className="mt-3 text-sm text-slate-500">
          {summary.response_count} response
          {summary.response_count === 1 ? "" : "s"} ·{" "}
          {summary.average_rating.toFixed(1)} average rating
        </p>
      ) : null}
    </section>
  );
}
