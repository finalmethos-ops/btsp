"use client";

import { FormEvent, useEffect, useState } from "react";
import {
  NotificationEventAdmin,
  NotificationTemplateAdmin,
  NotificationTemplateAdminWrite,
  createNotificationTemplateAdmin,
  listNotificationEventsAdmin,
  listNotificationTemplatesAdmin,
  retryNotificationEventAdmin,
  updateNotificationTemplateAdmin,
} from "@/lib/api";

const emptyTemplate: NotificationTemplateAdminWrite = {
  template_code: "",
  workflow_code: "BPP_PURCHASING",
  event_type: "",
  channel: "in_app",
  subject_template: "",
  body_template: "",
  recipient_strategy: "actor",
  recipient_config: {},
  is_active: true,
};

export function NotificationAdministrationPanel() {
  const [templates, setTemplates] = useState<NotificationTemplateAdmin[]>([]);
  const [events, setEvents] = useState<NotificationEventAdmin[]>([]);
  const [selectedCode, setSelectedCode] = useState<string | null>(null);
  const [form, setForm] =
    useState<NotificationTemplateAdminWrite>(emptyTemplate);
  const [recipientJson, setRecipientJson] = useState("{}");
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function refresh() {
    const [nextTemplates, nextEvents] = await Promise.all([
      listNotificationTemplatesAdmin(),
      listNotificationEventsAdmin(),
    ]);
    setTemplates(nextTemplates);
    setEvents(nextEvents);
  }

  useEffect(() => {
    void refresh().catch(() =>
      setError("Unable to load notification administration."),
    );
  }, []);

  function clear() {
    setSelectedCode(null);
    setForm(emptyTemplate);
    setRecipientJson("{}");
    setMessage(null);
    setError(null);
  }

  function selectTemplate(template: NotificationTemplateAdmin) {
    setSelectedCode(template.template_code);
    setForm({
      template_code: template.template_code,
      workflow_code: template.workflow_code,
      event_type: template.event_type,
      channel: template.channel,
      subject_template: template.subject_template,
      body_template: template.body_template,
      recipient_strategy: template.recipient_strategy,
      recipient_config: template.recipient_config,
      is_active: template.is_active,
    });
    setRecipientJson(JSON.stringify(template.recipient_config, null, 2));
    setMessage(null);
    setError(null);
  }

  function field<K extends keyof NotificationTemplateAdminWrite>(
    key: K,
    value: NotificationTemplateAdminWrite[K],
  ) {
    setForm((current) => ({ ...current, [key]: value }));
  }

  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setMessage(null);
    setError(null);
    try {
      const recipientConfig = JSON.parse(recipientJson) as Record<
        string,
        unknown
      >;
      const payload = { ...form, recipient_config: recipientConfig };
      if (selectedCode) {
        await updateNotificationTemplateAdmin(selectedCode, {
          workflow_code: payload.workflow_code,
          event_type: payload.event_type,
          channel: payload.channel,
          subject_template: payload.subject_template,
          body_template: payload.body_template,
          recipient_strategy: payload.recipient_strategy,
          recipient_config: payload.recipient_config,
          is_active: payload.is_active,
        });
        setMessage("Template updated.");
      } else {
        await createNotificationTemplateAdmin(payload);
        setMessage("Template created.");
      }
      await refresh();
      clear();
    } catch (reason) {
      setError(
        reason instanceof Error ? reason.message : "Unable to save template.",
      );
    }
  }

  async function retry(item: NotificationEventAdmin) {
    setError(null);
    try {
      await retryNotificationEventAdmin(item.notification_id);
      await refresh();
      setMessage(`Notification ${item.notification_id} requeued.`);
    } catch (reason) {
      setError(
        reason instanceof Error
          ? reason.message
          : "Unable to retry notification.",
      );
    }
  }

  return (
    <div className="space-y-8">
      <div>
        <h2 className="text-2xl font-bold">Notification administration</h2>
        <p className="mt-2 text-sm text-slate-600">
          Manage templates and inspect the durable delivery ledger.
        </p>
      </div>
      {message ? (
        <p className="rounded bg-green-50 p-3 text-sm text-green-700">
          {message}
        </p>
      ) : null}
      {error ? (
        <p className="rounded bg-red-50 p-3 text-sm text-red-700">{error}</p>
      ) : null}
      <div className="grid gap-6 lg:grid-cols-[1fr_440px]">
        <section>
          <h3 className="font-semibold">Templates</h3>
          <div className="mt-3 overflow-x-auto rounded border">
            <table className="w-full text-left text-sm">
              <thead className="bg-slate-100">
                <tr>
                  <th className="p-3">Template</th>
                  <th className="p-3">Event</th>
                  <th className="p-3">Channel</th>
                  <th className="p-3">Status</th>
                </tr>
              </thead>
              <tbody>
                {templates.map((template) => (
                  <tr className="border-t" key={template.template_code}>
                    <td className="p-3">
                      <button
                        className="font-medium underline"
                        onClick={() => selectTemplate(template)}
                        type="button"
                      >
                        {template.template_code}
                      </button>
                    </td>
                    <td className="p-3">{template.event_type}</td>
                    <td className="p-3">{template.channel}</td>
                    <td className="p-3">
                      {template.is_active ? "Active" : "Disabled"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
        <form className="rounded border p-4" onSubmit={save}>
          <div className="mb-4 flex justify-between">
            <h3 className="font-semibold">
              {selectedCode ? "Edit template" : "Create template"}
            </h3>
            <button className="text-sm underline" onClick={clear} type="button">
              Clear
            </button>
          </div>
          <label className="mb-3 block text-sm font-medium">
            Template code
            <input
              className="mt-1 w-full rounded border px-3 py-2"
              disabled={Boolean(selectedCode)}
              onChange={(event) =>
                field("template_code", event.target.value.toUpperCase())
              }
              required
              value={form.template_code}
            />
          </label>
          <div className="grid grid-cols-2 gap-3">
            <label className="mb-3 block text-sm font-medium">
              Workflow
              <input
                className="mt-1 w-full rounded border px-3 py-2"
                onChange={(event) => field("workflow_code", event.target.value)}
                required
                value={form.workflow_code}
              />
            </label>
            <label className="mb-3 block text-sm font-medium">
              Event type
              <input
                className="mt-1 w-full rounded border px-3 py-2"
                onChange={(event) => field("event_type", event.target.value)}
                required
                value={form.event_type}
              />
            </label>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <label className="mb-3 block text-sm font-medium">
              Channel
              <select
                className="mt-1 w-full rounded border px-3 py-2"
                onChange={(event) =>
                  field(
                    "channel",
                    event.target
                      .value as NotificationTemplateAdminWrite["channel"],
                  )
                }
                value={form.channel}
              >
                <option value="in_app">In app</option>
                <option value="email">Email</option>
                <option value="webhook">Webhook</option>
              </select>
            </label>
            <label className="mb-3 block text-sm font-medium">
              Recipients
              <select
                className="mt-1 w-full rounded border px-3 py-2"
                onChange={(event) =>
                  field(
                    "recipient_strategy",
                    event.target
                      .value as NotificationTemplateAdminWrite["recipient_strategy"],
                  )
                }
                value={form.recipient_strategy}
              >
                <option value="actor">Actor</option>
                <option value="workflow_role">Workflow role</option>
                <option value="permission_holders">Permission holders</option>
                <option value="region_admins">Region admins</option>
                <option value="store_users">Store users</option>
                <option value="static_recipients">Static recipients</option>
              </select>
            </label>
          </div>
          <label className="mb-3 block text-sm font-medium">
            Subject
            <input
              className="mt-1 w-full rounded border px-3 py-2"
              onChange={(event) =>
                field("subject_template", event.target.value)
              }
              required
              value={form.subject_template}
            />
          </label>
          <label className="mb-3 block text-sm font-medium">
            Body
            <textarea
              className="mt-1 min-h-24 w-full rounded border px-3 py-2"
              onChange={(event) => field("body_template", event.target.value)}
              required
              value={form.body_template}
            />
          </label>
          <label className="mb-3 block text-sm font-medium">
            Recipient configuration (JSON)
            <textarea
              className="mt-1 min-h-20 w-full rounded border px-3 py-2 font-mono text-xs"
              onChange={(event) => setRecipientJson(event.target.value)}
              value={recipientJson}
            />
          </label>
          <label className="mb-4 flex gap-2 text-sm">
            <input
              checked={form.is_active}
              onChange={(event) => field("is_active", event.target.checked)}
              type="checkbox"
            />
            Active
          </label>
          <button
            className="w-full rounded bg-slate-900 px-4 py-2 text-white"
            type="submit"
          >
            {selectedCode ? "Update template" : "Create template"}
          </button>
        </form>
      </div>
      <section>
        <h3 className="font-semibold">Recent delivery events</h3>
        <div className="mt-3 overflow-x-auto rounded border">
          <table className="w-full text-left text-sm">
            <thead className="bg-slate-100">
              <tr>
                <th className="p-3">ID</th>
                <th className="p-3">Template</th>
                <th className="p-3">Entity</th>
                <th className="p-3">Recipients</th>
                <th className="p-3">Status</th>
                <th className="p-3">Action</th>
              </tr>
            </thead>
            <tbody>
              {events.map((item) => (
                <tr className="border-t" key={item.notification_id}>
                  <td className="p-3">{item.notification_id}</td>
                  <td className="p-3">{item.template_code}</td>
                  <td className="p-3">
                    {item.entity_type}:{item.entity_id}
                  </td>
                  <td className="p-3">{item.resolved_recipients.length}</td>
                  <td className="p-3">
                    {item.status}
                    {item.error_message ? (
                      <span className="block text-xs text-red-700">
                        {item.error_message}
                      </span>
                    ) : null}
                  </td>
                  <td className="p-3">
                    {item.status === "failed" ? (
                      <button
                        className="underline"
                        onClick={() => void retry(item)}
                        type="button"
                      >
                        Requeue
                      </button>
                    ) : (
                      "—"
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
