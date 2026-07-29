"use client";

import { useEffect, useState } from "react";
import {
  EventFeedbackSummary,
  getEventFeedback,
} from "@/lib/event-feedback-api";

export function EventFeedbackAdministrationPanel({
  eventId,
}: {
  eventId: string;
}) {
  const [summary, setSummary] = useState<EventFeedbackSummary | null>(null);
  useEffect(() => {
    void getEventFeedback(eventId)
      .then(setSummary)
      .catch(() => undefined);
  }, [eventId]);
  return (
    <section className="rounded-2xl border border-white/10 bg-slate-950/30 p-4">
      <p className="brand-eyebrow">Post-event analytics</p>
      <h4 className="font-bold">Attendee feedback</h4>
      <div className="mt-3 grid gap-3 sm:grid-cols-3">
        <Metric
          label="Responses"
          value={String(summary?.response_count ?? 0)}
        />
        <Metric
          label="Average rating"
          value={
            summary?.average_rating == null
              ? "—"
              : `${summary.average_rating.toFixed(1)} / 5`
          }
        />
        <Metric
          label="Comments"
          value={String(
            summary?.responses.filter((response) => response.comments).length ??
              0,
          )}
        />
        <Metric
          label="Response rate"
          value={summary ? `${summary.response_rate.toFixed(1)}%` : "—"}
        />
      </div>
      {summary?.responses.length ? (
        <div className="mt-3 max-h-56 space-y-2 overflow-auto">
          {summary.responses.map((response) => (
            <article
              className="rounded-lg border border-white/10 p-3 text-sm"
              key={response.id}
            >
              <strong>{response.rating} / 5</strong>
              {response.comments ? (
                <p className="mt-1 text-slate-300">{response.comments}</p>
              ) : null}
            </article>
          ))}
        </div>
      ) : (
        <p className="mt-3 text-sm text-slate-400">
          No feedback has been submitted yet.
        </p>
      )}
      {summary?.feedback_by_attendee_type.length ? (
        <div className="mt-4 grid gap-2 sm:grid-cols-2">
          {summary.feedback_by_attendee_type.map((item) => (
            <div
              className="rounded-lg border border-white/10 p-3 text-sm"
              key={item.attendee_type}
            >
              <strong className="capitalize">
                {item.attendee_type.replaceAll("_", " ")}
              </strong>
              <span className="mt-1 block text-slate-400">
                {item.response_count} response
                {item.response_count === 1 ? "" : "s"} ·{" "}
                {item.average_rating == null
                  ? "—"
                  : `${item.average_rating.toFixed(1)} / 5`}
              </span>
            </div>
          ))}
        </div>
      ) : null}
    </section>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-white/10 p-3">
      <span className="block text-xs font-bold uppercase text-slate-400">
        {label}
      </span>
      <strong className="mt-1 block text-xl">{value}</strong>
    </div>
  );
}
