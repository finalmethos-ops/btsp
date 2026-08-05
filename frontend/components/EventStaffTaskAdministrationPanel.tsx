"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
import { ManagedEvent } from "@/lib/event-admin-api";
import {
  createEventStaffTask,
  downloadEventStaffTaskEvidence,
  EventStaffTask,
  EventStaffTaskPriority,
  EventStaffTaskPhase,
  EventStaffTaskStatus,
  exportEventStaffTasks,
  listEventStaffTasks,
  updateEventStaffTask,
} from "@/lib/event-staff-task-api";

const priorities: EventStaffTaskPriority[] = [
  "low",
  "normal",
  "high",
  "urgent",
];
const statuses: EventStaffTaskStatus[] = [
  "open",
  "in_progress",
  "blocked",
  "done",
  "cancelled",
];
const phases: EventStaffTaskPhase[] = ["pre_event", "live_event", "post_event"];

const localDateTime = (value: string) => {
  const date = new Date(value);
  return new Date(date.getTime() - date.getTimezoneOffset() * 60_000)
    .toISOString()
    .slice(0, 16);
};

export function EventStaffTaskAdministrationPanel({
  event,
  subEventId,
}: {
  event: ManagedEvent;
  subEventId?: string;
}) {
  const [tasks, setTasks] = useState<EventStaffTask[]>([]);
  const [editing, setEditing] = useState<EventStaffTask | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [phaseFilter, setPhaseFilter] = useState<EventStaffTaskPhase | "all">(
    "all",
  );
  const [statusFilter, setStatusFilter] = useState<
    EventStaffTaskStatus | "all"
  >("all");
  const [assigneeFilter, setAssigneeFilter] = useState("all");
  const [taskSearch, setTaskSearch] = useState("");
  const [selectedTaskSubEventId, setSelectedTaskSubEventId] = useState(
    subEventId ?? "",
  );
  const operationalStaffMembers = event.memberships.filter(
    (member) =>
      ["staff", "admin", "team_lead", "dockmaster", "overseer"].includes(
        member.membership_type,
      ) || Boolean(member.loadout_role),
  );
  const staffMembers = operationalStaffMembers.filter(
    (member) =>
      !subEventId ||
      !member.sub_event_scope_configured ||
      member.sub_event_ids.includes(subEventId),
  );
  const eligibleStaffMembers = operationalStaffMembers.filter(
    (member) =>
      !selectedTaskSubEventId ||
      !member.sub_event_scope_configured ||
      member.sub_event_ids.includes(selectedTaskSubEventId),
  );
  const load = useCallback(
    () =>
      listEventStaffTasks(event.id)
        .then(setTasks)
        .catch((caught) => {
          setError(
            caught instanceof Error
              ? caught.message
              : "Unable to load staff tasks.",
          );
        }),
    [event.id],
  );

  useEffect(() => {
    setEditing(null);
    setSelectedTaskSubEventId(subEventId ?? "");
    void load();
    const timer = window.setInterval(() => void load(), 30_000);
    return () => window.clearInterval(timer);
  }, [load, subEventId]);

  async function save(formEvent: FormEvent<HTMLFormElement>) {
    formEvent.preventDefault();
    const form = formEvent.currentTarget;
    const data = new FormData(form);
    const dueAt = String(data.get("due_at") || "");
    setBusy(true);
    setError(null);
    try {
      const payload = {
        assigned_membership_id: String(data.get("assigned_membership_id")),
        sub_event_id: String(data.get("sub_event_id") || "") || null,
        vendor_hall_booth_id: editing?.vendor_hall_booth_id ?? null,
        title: String(data.get("title")),
        description: String(data.get("description") || "") || null,
        priority: String(data.get("priority")) as EventStaffTaskPriority,
        status: String(data.get("status")) as EventStaffTaskStatus,
        task_phase: String(data.get("task_phase")) as EventStaffTaskPhase,
        due_at: dueAt ? new Date(dueAt).toISOString() : null,
      };
      if (editing) {
        await updateEventStaffTask(event.id, editing.id, payload);
      } else {
        await createEventStaffTask(event.id, payload);
      }
      form.reset();
      setEditing(null);
      setSelectedTaskSubEventId(subEventId ?? "");
      await load();
    } catch (caught) {
      setError(
        caught instanceof Error ? caught.message : "Unable to save the task.",
      );
    } finally {
      setBusy(false);
    }
  }

  async function cancelTask(task: EventStaffTask) {
    if (!window.confirm(`Cancel "${task.title}"?`)) return;
    setBusy(true);
    setError(null);
    try {
      await updateEventStaffTask(event.id, task.id, {
        assigned_membership_id: task.assigned_membership_id,
        sub_event_id: task.sub_event_id,
        vendor_hall_booth_id: task.vendor_hall_booth_id,
        title: task.title,
        description: task.description,
        priority: task.priority,
        status: "cancelled",
        task_phase: task.task_phase,
        due_at: task.due_at,
      });
      if (editing?.id === task.id) setEditing(null);
      await load();
    } catch (caught) {
      setError(
        caught instanceof Error ? caught.message : "Unable to cancel the task.",
      );
    } finally {
      setBusy(false);
    }
  }

  async function downloadEvidence(taskId: string, attachmentId: string) {
    setError(null);
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
    } catch (caught) {
      setError(
        caught instanceof Error
          ? caught.message
          : "Unable to download task evidence.",
      );
    }
  }

  async function exportTasks() {
    setBusy(true);
    setError(null);
    try {
      const { blob, filename } = await exportEventStaffTasks(event.id);
      const anchor = document.createElement("a");
      anchor.href = URL.createObjectURL(blob);
      anchor.download = filename ?? `${event.slug}-staff-tasks.xlsx`;
      anchor.click();
      URL.revokeObjectURL(anchor.href);
    } catch (caught) {
      setError(
        caught instanceof Error
          ? caught.message
          : "Unable to export the staff task report.",
      );
    } finally {
      setBusy(false);
    }
  }

  const scopedTasks = tasks.filter(
    (task) => !subEventId || task.sub_event_id === subEventId,
  );
  const isOverdue = (task: EventStaffTask) =>
    Boolean(
      task.due_at &&
        !["done", "cancelled"].includes(task.status) &&
        new Date(task.due_at) < new Date(),
    );
  const priorityRank: Record<EventStaffTaskPriority, number> = {
    urgent: 0,
    high: 1,
    normal: 2,
    low: 3,
  };
  const normalizedSearch = taskSearch.trim().toLowerCase();
  const visibleTasks = scopedTasks
    .filter((task) => phaseFilter === "all" || task.task_phase === phaseFilter)
    .filter((task) => statusFilter === "all" || task.status === statusFilter)
    .filter(
      (task) =>
        assigneeFilter === "all" ||
        task.assigned_membership_id === assigneeFilter,
    )
    .filter(
      (task) =>
        !normalizedSearch ||
        [
          task.title,
          task.description,
          task.assigned_display_name,
          task.vendor_hall_booth_name,
        ].some((value) => value?.toLowerCase().includes(normalizedSearch)),
    )
    .sort((left, right) => {
      const terminalDifference =
        Number(["done", "cancelled"].includes(left.status)) -
        Number(["done", "cancelled"].includes(right.status));
      if (terminalDifference) return terminalDifference;
      const overdueDifference =
        Number(isOverdue(right)) - Number(isOverdue(left));
      if (overdueDifference) return overdueDifference;
      const priorityDifference =
        priorityRank[left.priority] - priorityRank[right.priority];
      if (priorityDifference) return priorityDifference;
      return (
        new Date(left.due_at ?? left.updated_at).getTime() -
        new Date(right.due_at ?? right.updated_at).getTime()
      );
    });
  const openTaskCount = scopedTasks.filter(
    (task) => !["done", "cancelled"].includes(task.status),
  ).length;
  const taskMetrics = [
    ["Active", openTaskCount],
    [
      "In progress",
      scopedTasks.filter((task) => task.status === "in_progress").length,
    ],
    ["Blocked", scopedTasks.filter((task) => task.status === "blocked").length],
    ["Overdue", scopedTasks.filter(isOverdue).length],
    ["Completed", scopedTasks.filter((task) => task.status === "done").length],
  ] as const;
  const staffWorkload = staffMembers
    .map((member) => {
      const assigned = scopedTasks.filter(
        (task) => task.assigned_membership_id === member.id,
      );
      const cancelled = assigned.filter(
        (task) => task.status === "cancelled",
      ).length;
      const completed = assigned.filter(
        (task) => task.status === "done",
      ).length;
      const eligible = assigned.length - cancelled;
      return {
        id: member.id,
        name: member.display_name,
        total: assigned.length,
        active: assigned.filter(
          (task) => !["done", "cancelled"].includes(task.status),
        ).length,
        blocked: assigned.filter((task) => task.status === "blocked").length,
        overdue: assigned.filter(isOverdue).length,
        completed,
        completionRate: eligible ? Math.round((completed / eligible) * 100) : 0,
      };
    })
    .filter((item) => item.total)
    .sort(
      (left, right) =>
        right.overdue - left.overdue ||
        right.blocked - left.blocked ||
        right.active - left.active ||
        left.name.localeCompare(right.name),
    );

  return (
    <section className="event-ui rounded-2xl border bg-white p-5">
      <p className="brand-eyebrow">Onsite staff operations</p>
      <h3 className="text-xl font-bold">Staff tasks</h3>
      <div className="mt-1 flex flex-wrap items-center justify-between gap-3">
        <p className="text-sm text-slate-600">
          Assign scoped work to onsite staff and track completion during the
          event. {openTaskCount} active.
        </p>
        <div className="flex flex-wrap gap-2">
          <button
            className="rounded-lg border px-3 py-2 text-sm font-bold"
            disabled={busy}
            onClick={() => void exportTasks()}
            type="button"
          >
            Export Excel
          </button>
          <button
            className="rounded-lg border px-3 py-2 text-sm font-bold"
            onClick={() => void load()}
            type="button"
          >
            Refresh status
          </button>
        </div>
      </div>
      {error ? (
        <p className="mt-3 rounded-lg bg-red-50 p-3 text-red-800">{error}</p>
      ) : null}
      <div className="event-task-admin-summary">
        {taskMetrics.map(([label, value]) => (
          <div className="event-task-admin-metric" key={label}>
            <span>{label}</span>
            <strong>{value}</strong>
          </div>
        ))}
      </div>
      <details className="event-task-workload">
        <summary>
          Staff workload
          <span>{staffWorkload.length} assigned</span>
        </summary>
        <div className="event-task-workload-grid">
          {staffWorkload.map((item) => (
            <article key={item.id}>
              <strong>{item.name}</strong>
              <span>
                {item.active} active · {item.completed}/{item.total} completed
              </span>
              <span>
                {item.blocked} blocked · {item.overdue} overdue ·{" "}
                {item.completionRate}% complete
              </span>
            </article>
          ))}
          {!staffWorkload.length ? (
            <p>No staff assignments are available in this scope.</p>
          ) : null}
        </div>
      </details>
      <div className="mt-4 grid gap-5 lg:grid-cols-2">
        <form
          className="grid gap-3 rounded-xl bg-slate-50 p-4"
          key={editing?.id ?? "new-staff-task"}
          onSubmit={save}
        >
          <label className="font-semibold">
            Related sub-event
            <select
              className="mt-1 w-full rounded-lg border bg-white p-3"
              disabled={Boolean(subEventId)}
              name="sub_event_id"
              onChange={(input) =>
                setSelectedTaskSubEventId(input.currentTarget.value)
              }
              value={selectedTaskSubEventId}
            >
              {!subEventId ? <option value="">Entire event</option> : null}
              {event.sub_events.map((subEvent) => (
                <option key={subEvent.id} value={subEvent.id}>
                  {subEvent.name}
                </option>
              ))}
            </select>
            {subEventId ? (
              <input name="sub_event_id" type="hidden" value={subEventId} />
            ) : null}
          </label>
          <label className="font-semibold">
            Assign to
            <select
              className="mt-1 w-full rounded-lg border bg-white p-3"
              defaultValue={editing?.assigned_membership_id}
              key={`${editing?.id ?? "new"}-${selectedTaskSubEventId}`}
              name="assigned_membership_id"
              required
            >
              <option value="">Select eligible staff</option>
              {eligibleStaffMembers.map((member) => (
                <option key={member.id} value={member.id}>
                  {member.display_name} · {member.membership_type}
                </option>
              ))}
            </select>
            {!eligibleStaffMembers.length ? (
              <span className="mt-1 block text-xs text-red-700">
                No operations personnel have access to this sub-event.
              </span>
            ) : null}
          </label>
          <label className="font-semibold">
            Task phase
            <select
              className="mt-1 w-full rounded-lg border bg-white p-3"
              defaultValue={editing?.task_phase ?? "live_event"}
              name="task_phase"
            >
              {phases.map((phase) => (
                <option key={phase} value={phase}>
                  {phase.replaceAll("_", " ")}
                </option>
              ))}
            </select>
          </label>
          <input
            className="rounded-lg border bg-white p-3"
            defaultValue={editing?.title}
            name="title"
            placeholder="Task title"
            required
          />
          <textarea
            className="rounded-lg border bg-white p-3"
            defaultValue={editing?.description ?? ""}
            name="description"
            placeholder="Task instructions"
          />
          <div className="grid gap-3 sm:grid-cols-2">
            <select
              className="rounded-lg border bg-white p-3"
              defaultValue={editing?.priority ?? "normal"}
              name="priority"
            >
              {priorities.map((priority) => (
                <option key={priority} value={priority}>
                  {priority.replace("_", " ")}
                </option>
              ))}
            </select>
            <select
              className="rounded-lg border bg-white p-3"
              defaultValue={editing?.status ?? "open"}
              name="status"
            >
              {statuses.map((status) => (
                <option key={status} value={status}>
                  {status.replace("_", " ")}
                </option>
              ))}
            </select>
          </div>
          <label className="font-semibold">
            Due at
            <input
              className="mt-1 w-full rounded-lg border bg-white p-3"
              defaultValue={
                editing?.due_at ? localDateTime(editing.due_at) : undefined
              }
              name="due_at"
              type="datetime-local"
            />
          </label>
          <button
            className="rounded-xl bg-blue-800 p-3 font-bold text-white disabled:bg-slate-400"
            disabled={busy || !eligibleStaffMembers.length}
          >
            {busy ? "Saving…" : editing ? "Save task" : "Create staff task"}
          </button>
          {editing ? (
            <button
              className="rounded-xl border p-3 font-bold"
              onClick={() => {
                setEditing(null);
                setSelectedTaskSubEventId(subEventId ?? "");
              }}
              type="button"
            >
              Cancel editing
            </button>
          ) : null}
        </form>
        <div className="max-h-[34rem] space-y-3 overflow-auto">
          <div className="event-task-admin-filters">
            <input
              aria-label="Search staff tasks"
              onChange={(event) => setTaskSearch(event.target.value)}
              placeholder="Search tasks, staff, or booths"
              type="search"
              value={taskSearch}
            />
            <select
              aria-label="Filter by task phase"
              onChange={(event) =>
                setPhaseFilter(
                  event.target.value as EventStaffTaskPhase | "all",
                )
              }
              value={phaseFilter}
            >
              <option value="all">All task phases</option>
              {phases.map((phase) => (
                <option key={phase} value={phase}>
                  {phase.replaceAll("_", " ")}
                </option>
              ))}
            </select>
            <select
              aria-label="Filter by task status"
              onChange={(event) =>
                setStatusFilter(
                  event.target.value as EventStaffTaskStatus | "all",
                )
              }
              value={statusFilter}
            >
              <option value="all">All statuses</option>
              {statuses.map((status) => (
                <option key={status} value={status}>
                  {status.replaceAll("_", " ")}
                </option>
              ))}
            </select>
            <select
              aria-label="Filter by assignee"
              onChange={(event) => setAssigneeFilter(event.target.value)}
              value={assigneeFilter}
            >
              <option value="all">All assigned staff</option>
              {staffMembers.map((member) => (
                <option key={member.id} value={member.id}>
                  {member.display_name}
                </option>
              ))}
            </select>
          </div>
          {visibleTasks.map((task) => (
            <article className="rounded-xl border p-4" key={task.id}>
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <span className="text-xs font-bold uppercase text-blue-700">
                    {task.task_phase.replace("_", " ")} · {task.priority} ·{" "}
                    {task.status.replace("_", " ")}
                  </span>
                  <h4 className="font-bold">{task.title}</h4>
                  <p className="text-sm text-slate-600">
                    {task.assigned_display_name} ·{" "}
                    {task.sub_event_name ?? "Entire event"}
                  </p>
                  {task.vendor_hall_booth_name ? (
                    <p className="text-sm font-semibold text-slate-700">
                      Vendor Hall booth: {task.vendor_hall_booth_name}
                    </p>
                  ) : null}
                </div>
                <div className="flex gap-3">
                  <button
                    className="text-sm font-bold text-blue-700"
                    onClick={() => {
                      setEditing(task);
                      setSelectedTaskSubEventId(task.sub_event_id ?? "");
                    }}
                    type="button"
                  >
                    Edit
                  </button>
                  {!["done", "cancelled"].includes(task.status) ? (
                    <button
                      className="text-sm font-bold text-red-700"
                      disabled={busy}
                      onClick={() => void cancelTask(task)}
                      type="button"
                    >
                      Cancel
                    </button>
                  ) : null}
                </div>
              </div>
              {task.description ? (
                <p className="mt-2 text-sm text-slate-600">
                  {task.description}
                </p>
              ) : null}
              {task.status_note ? (
                <p className="mt-2 rounded-lg bg-amber-50 p-2 text-sm font-semibold text-amber-950">
                  Staff note: {task.status_note}
                </p>
              ) : null}
              {task.completed_at ? (
                <p className="mt-2 text-xs font-semibold text-green-800">
                  Completed {new Date(task.completed_at).toLocaleString()}
                  {task.completed_by ? ` by ${task.completed_by}` : ""}
                </p>
              ) : null}
              {task.attachments.length ? (
                <div className="mt-2 grid gap-1">
                  {task.attachments.map((attachment) => (
                    <button
                      className="w-fit max-w-full break-all text-left text-sm font-bold text-blue-700 underline"
                      key={attachment.id}
                      onClick={() =>
                        void downloadEvidence(task.id, attachment.id)
                      }
                      type="button"
                    >
                      Evidence: {attachment.filename}
                    </button>
                  ))}
                </div>
              ) : null}
              {task.due_at ? (
                <p className="mt-2 text-xs text-slate-500">
                  {isOverdue(task) ? (
                    <strong className="text-red-600">Overdue · </strong>
                  ) : null}
                  Due {new Date(task.due_at).toLocaleString()}
                </p>
              ) : null}
            </article>
          ))}
          {!visibleTasks.length ? (
            <p className="rounded-xl border border-dashed p-5 text-slate-500">
              No staff tasks match this sub-event and phase.
            </p>
          ) : null}
        </div>
      </div>
    </section>
  );
}
