"use client";

import { FormEvent, useEffect, useState } from "react";
import { useEventBranding } from "@/components/EventBrandingProvider";
import {
  EventStaffTask,
  EventStaffTaskStatus,
  downloadEventStaffTaskEvidence,
  listMyEventStaffTasks,
  updateMyEventStaffTaskStatus,
  uploadEventStaffTaskEvidence,
} from "@/lib/event-staff-task-api";

const nextStatuses: Record<EventStaffTaskStatus, EventStaffTaskStatus> = {
  open: "in_progress",
  in_progress: "done",
  blocked: "in_progress",
  done: "open",
  cancelled: "cancelled",
};

type EventStaffTaskLandingProps = {
  eventId: string;
  subEventId: string;
};

export function EventStaffTaskLanding({
  eventId,
  subEventId,
}: EventStaffTaskLandingProps) {
  const { brandedClassName, brandedStyle } = useEventBranding();
  const [tasks, setTasks] = useState<EventStaffTask[]>([]);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [loaded, setLoaded] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [notes, setNotes] = useState<Record<string, string>>({});

  useEffect(() => {
    let active = true;
    const refresh = () =>
      void listMyEventStaffTasks()
        .then((items) => {
          if (!active) return;
          setTasks(
            items.filter(
              (task) =>
                task.event_id === eventId && task.sub_event_id === subEventId,
            ),
          );
          setLoaded(true);
        })
        .catch(() => {
          if (!active) return;
          setMessage("Assigned tasks could not be loaded. Please try again.");
          setLoaded(true);
        });
    refresh();
    const timer = window.setInterval(refresh, 60_000);
    return () => {
      active = false;
      window.clearInterval(timer);
    };
  }, [eventId, subEventId]);

  async function advance(
    task: EventStaffTask,
    status = nextStatuses[task.status],
  ) {
    setBusyId(task.id);
    setMessage(null);
    try {
      const updated = await updateMyEventStaffTaskStatus(
        task.id,
        status,
        notes[task.id],
      );
      setTasks((current) =>
        current.map((item) => (item.id === updated.id ? updated : item)),
      );
      setNotes((current) => ({ ...current, [task.id]: "" }));
      setMessage(
        updated.status === "done"
          ? "Task completed. Event administrators have been notified."
          : updated.status === "blocked"
            ? "Task marked blocked. Your note is visible to event administrators."
            : "Task started.",
      );
    } catch {
      setMessage("The task status could not be updated. Please try again.");
    } finally {
      setBusyId(null);
    }
  }

  async function uploadEvidence(
    task: EventStaffTask,
    formEvent: FormEvent<HTMLFormElement>,
  ) {
    formEvent.preventDefault();
    const form = formEvent.currentTarget;
    const file = new FormData(form).get("evidence");
    if (!(file instanceof File) || !file.size) return;
    setBusyId(task.id);
    setMessage(null);
    try {
      const attachment = await uploadEventStaffTaskEvidence(task.id, file);
      setTasks((current) =>
        current.map((item) =>
          item.id === task.id
            ? { ...item, attachments: [...item.attachments, attachment] }
            : item,
        ),
      );
      form.reset();
      setMessage("Evidence photo uploaded.");
    } catch {
      setMessage("The evidence photo could not be uploaded. Please try again.");
    } finally {
      setBusyId(null);
    }
  }

  async function downloadEvidence(taskId: string, attachmentId: string) {
    setMessage(null);
    try {
      const { blob, filename } = await downloadEventStaffTaskEvidence(
        taskId,
        attachmentId,
      );
      const anchor = document.createElement("a");
      anchor.href = URL.createObjectURL(blob);
      anchor.download = filename ?? "task-evidence";
      anchor.click();
      URL.revokeObjectURL(anchor.href);
    } catch {
      setMessage("The evidence photo could not be downloaded.");
    }
  }

  const activeTasks = tasks.filter(
    (task) => !["done", "cancelled"].includes(task.status),
  );
  const visibleTasks = [...tasks].sort(
    (left, right) =>
      Number(["done", "cancelled"].includes(left.status)) -
      Number(["done", "cancelled"].includes(right.status)),
  );
  if (!loaded) return null;

  return (
    <section className="event-ui event-task-panel mb-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="brand-eyebrow">Staff tasks</p>
          <h2>Your onsite task list</h2>
          <p>
            {activeTasks.length} active task
            {activeTasks.length === 1 ? "" : "s"} assigned.
          </p>
        </div>
      </div>
      {message ? (
        <p aria-live="polite" className="event-inline-notice mt-3">
          {message}
        </p>
      ) : null}
      <div className="event-task-list">
        {!visibleTasks.length ? (
          <div className="event-empty-state">
            No staff tasks are assigned to you for this part of the event.
          </div>
        ) : null}
        {visibleTasks.slice(0, 8).map((task) => (
          <article
            className={brandedClassName(task.event_id, "event-task-card")}
            key={task.id}
            style={brandedStyle(task.event_id)}
          >
            <div>
              <p className="brand-eyebrow">{task.event_name}</p>
              <h3>{task.title}</h3>
              <p>
                {task.sub_event_name ?? "Entire event"} ·{" "}
                {task.task_phase.replaceAll("_", " ")} · {task.priority} ·{" "}
                {task.status.replaceAll("_", " ")}
              </p>
              {task.vendor_hall_booth_name ? (
                <p className="font-bold">
                  Vendor Hall booth: {task.vendor_hall_booth_name}
                </p>
              ) : null}
              {task.due_at &&
              task.status !== "done" &&
              new Date(task.due_at) < new Date() ? (
                <p className="font-bold text-red-600">
                  Overdue · due {new Date(task.due_at).toLocaleString()}
                </p>
              ) : null}
              {task.description ? <p>{task.description}</p> : null}
              {task.status_note ? (
                <p className="event-task-status-note">
                  Latest note: {task.status_note}
                </p>
              ) : null}
              {task.completed_at ? (
                <p>Completed {new Date(task.completed_at).toLocaleString()}</p>
              ) : null}
              {task.attachments.length ? (
                <div className="event-task-evidence-list">
                  {task.attachments.map((attachment) => (
                    <button
                      key={attachment.id}
                      onClick={() =>
                        void downloadEvidence(task.id, attachment.id)
                      }
                      type="button"
                    >
                      View evidence · {attachment.filename}
                    </button>
                  ))}
                </div>
              ) : null}
            </div>
            {["done", "cancelled"].includes(task.status) ? (
              <span className="event-status-chip">
                {task.status === "done" ? "Completed" : "Cancelled"}
              </span>
            ) : task.status === "in_progress" ? (
              <div className="event-task-update">
                <label htmlFor={`task-note-${task.id}`}>
                  Completion or blocker note
                </label>
                <textarea
                  id={`task-note-${task.id}`}
                  onChange={(event) =>
                    setNotes((current) => ({
                      ...current,
                      [task.id]: event.target.value,
                    }))
                  }
                  placeholder="Optional details for the event administrator"
                  value={notes[task.id] ?? ""}
                />
                <div className="event-task-actions">
                  <button
                    className="event-task-secondary"
                    disabled={busyId === task.id}
                    onClick={() => void advance(task, "blocked")}
                    type="button"
                  >
                    Mark blocked
                  </button>
                  <button
                    className="brand-button"
                    disabled={busyId === task.id}
                    onClick={() => void advance(task, "done")}
                    type="button"
                  >
                    Mark complete
                  </button>
                </div>
                <form
                  className="event-task-evidence-upload"
                  onSubmit={(event) => void uploadEvidence(task, event)}
                >
                  <input
                    accept="image/jpeg,image/png,image/webp"
                    capture="environment"
                    name="evidence"
                    required
                    type="file"
                  />
                  <button
                    className="event-task-secondary"
                    disabled={busyId === task.id}
                    type="submit"
                  >
                    Upload evidence photo
                  </button>
                </form>
              </div>
            ) : (
              <button
                className="brand-button"
                disabled={busyId === task.id}
                onClick={() => void advance(task)}
                type="button"
              >
                {task.status === "blocked" ? "Resume task" : "Start task"}
              </button>
            )}
          </article>
        ))}
      </div>
    </section>
  );
}
