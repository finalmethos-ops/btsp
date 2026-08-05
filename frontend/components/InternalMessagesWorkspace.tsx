"use client";

import Link from "next/link";
import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import {
  InternalMessage,
  listInternalMessages,
  listMessageRecipients,
  markInternalMessageRead,
  MessageRecipient,
  sendInternalMessage,
} from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { usesCalendarEventLanding } from "@/lib/event-landing";

export function InternalMessagesWorkspace() {
  const { user } = useAuth();
  const eventView = usesCalendarEventLanding(user);
  const [messages, setMessages] = useState<InternalMessage[]>([]);
  const [recipients, setRecipients] = useState<MessageRecipient[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [recipientEmail, setRecipientEmail] = useState("");
  const [subject, setSubject] = useState("");
  const [body, setBody] = useState("");
  const [replyBody, setReplyBody] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [sending, setSending] = useState(false);

  const refresh = useCallback(async () => {
    const [nextMessages, nextRecipients] = await Promise.all([
      listInternalMessages(),
      eventView ? Promise.resolve([]) : listMessageRecipients(),
    ]);
    setMessages(nextMessages);
    setRecipients(nextRecipients);
    setRecipientEmail((current) => current || nextRecipients[0]?.email || "");
    setSelectedId(
      (current) => current || nextMessages[0]?.conversation_id || null,
    );
  }, [eventView]);

  useEffect(() => {
    void refresh().catch((caught: unknown) =>
      setError(
        caught instanceof Error ? caught.message : "Unable to load messages.",
      ),
    );
  }, [refresh]);

  const conversations = useMemo(() => {
    const grouped = new Map<string, InternalMessage[]>();
    for (const message of messages) {
      const thread = grouped.get(message.conversation_id) ?? [];
      thread.push(message);
      grouped.set(message.conversation_id, thread);
    }
    return [...grouped.entries()]
      .map(([id, items]) => ({
        id,
        messages: items.sort((a, b) => a.id - b.id),
        latest: items.reduce((latest, item) =>
          item.id > latest.id ? item : latest,
        ),
        unread: items.filter(
          (item) => item.recipient_email === user?.email && !item.read_at,
        ).length,
      }))
      .sort((a, b) => b.latest.id - a.latest.id);
  }, [messages, user?.email]);
  const selected =
    conversations.find((item) => item.id === selectedId) ?? conversations[0];

  async function newConversation(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSending(true);
    setError(null);
    try {
      const message = await sendInternalMessage({
        recipient_email: recipientEmail,
        subject,
        body,
      });
      setSubject("");
      setBody("");
      setSelectedId(message.conversation_id);
      await refresh();
    } catch (caught) {
      setError(
        caught instanceof Error ? caught.message : "Unable to send message",
      );
    } finally {
      setSending(false);
    }
  }

  async function openConversation(id: string) {
    setSelectedId(id);
    const thread = conversations.find((item) => item.id === id);
    const unread =
      thread?.messages.filter(
        (item) => item.recipient_email === user?.email && !item.read_at,
      ) ?? [];
    await Promise.all(unread.map((item) => markInternalMessageRead(item.id)));
    if (unread.length) await refresh();
  }

  async function reply(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selected || !user) return;
    const first = selected.messages[0];
    const latest = selected.latest;
    const other =
      first.sender_email === user.email
        ? first.recipient_email
        : first.sender_email;
    setSending(true);
    setError(null);
    try {
      await sendInternalMessage({
        recipient_email: other,
        subject: first.subject.startsWith("Re:")
          ? first.subject
          : `Re: ${first.subject}`,
        body: replyBody,
        reply_to_message_id: latest.id,
      });
      setReplyBody("");
      await refresh();
      setSelectedId(selected.id);
    } catch (caught) {
      setError(
        caught instanceof Error ? caught.message : "Unable to send reply",
      );
    } finally {
      setSending(false);
    }
  }

  return (
    <main
      className={`mx-auto max-w-[1500px] p-4 sm:p-8 ${eventView ? "event-ui event-message-workspace" : ""}`}
    >
      <header className="mb-7">
        <Link
          className="text-sm text-slate-600"
          href={eventView ? "/events/calendar" : "/"}
        >
          ← {eventView ? "Event calendar" : "Command center"}
        </Link>
        <p className="brand-eyebrow mt-4">Internal communications</p>
        <h1 className="mt-2 text-3xl font-bold">Conversations</h1>
        <p className="mt-2 text-slate-600">
          Keep issue discussions and resolutions together in a private
          conversation.
        </p>
      </header>
      {error ? (
        <p className="mb-4 rounded-xl bg-red-50 p-3 text-sm text-red-800">
          {error}
        </p>
      ) : null}
      <div
        className={`event-message-grid grid gap-5 ${eventView ? "xl:grid-cols-[320px_1fr]" : "xl:grid-cols-[320px_310px_1fr]"}`}
      >
        {!eventView ? (
          <form
            className="h-fit rounded-2xl bg-white p-5"
            onSubmit={newConversation}
          >
            <h2 className="text-lg font-bold">New conversation</h2>
            <label className="mt-4 block text-sm font-semibold">
              Recipient
              <select
                className="mt-1 w-full rounded-lg border p-3"
                onChange={(e) => setRecipientEmail(e.target.value)}
                required
                value={recipientEmail}
              >
                {recipients.map((item) => (
                  <option key={item.email} value={item.email}>
                    {item.display_name} — {item.email}
                  </option>
                ))}
              </select>
            </label>
            <label className="mt-3 block text-sm font-semibold">
              Subject
              <input
                className="mt-1 w-full rounded-lg border p-3"
                maxLength={255}
                onChange={(e) => setSubject(e.target.value)}
                required
                value={subject}
              />
            </label>
            <label className="mt-3 block text-sm font-semibold">
              Message
              <textarea
                className="mt-1 min-h-32 w-full rounded-lg border p-3"
                maxLength={10000}
                onChange={(e) => setBody(e.target.value)}
                required
                value={body}
              />
            </label>
            <button className="brand-button mt-4 w-full" disabled={sending}>
              Start conversation
            </button>
          </form>
        ) : null}
        <section className="event-message-list rounded-2xl bg-white p-3">
          <h2 className="px-2 py-2 text-lg font-bold">Your conversations</h2>
          <div className="event-message-list-scroll max-h-[70vh] space-y-2 overflow-y-auto">
            {conversations.map((thread) => {
              const first = thread.messages[0];
              const other =
                first.sender_email === user?.email
                  ? first.recipient_email
                  : first.sender_email;
              return (
                <button
                  className={`w-full rounded-xl border p-3 text-left ${selected?.id === thread.id ? "selected-object" : "border-slate-200"}`}
                  key={thread.id}
                  onClick={() => void openConversation(thread.id)}
                >
                  <div className="flex justify-between gap-2">
                    <strong className="truncate">{first.subject}</strong>
                    {thread.unread ? (
                      <span className="rounded-full bg-yellow-400 px-2 text-xs font-bold">
                        {thread.unread}
                      </span>
                    ) : null}
                  </div>
                  <span className="block truncate text-xs text-slate-500">
                    {eventView ? "Event contact" : other}
                  </span>
                  <p className="mt-1 truncate text-sm text-slate-600">
                    {thread.latest.body}
                  </p>
                </button>
              );
            })}
            {!conversations.length ? (
              <p className="p-5 text-center text-sm text-slate-500">
                No conversations yet.
              </p>
            ) : null}
          </div>
        </section>
        <section className="event-message-thread flex min-h-[620px] flex-col rounded-2xl bg-white p-5">
          {selected ? (
            <>
              <div className="border-b pb-4">
                <h2 className="text-xl font-bold">
                  {selected.messages[0].subject}
                </h2>
                <p className="text-xs text-slate-500">
                  {selected.messages.length} message
                  {selected.messages.length === 1 ? "" : "s"}
                </p>
              </div>
              <div className="flex-1 space-y-3 overflow-y-auto py-5">
                {selected.messages.map((message) => {
                  const mine = message.sender_email === user?.email;
                  return (
                    <article
                      className={`event-message-bubble max-w-[85%] rounded-2xl p-4 ${mine ? "ml-auto bg-blue-900 text-white" : "bg-slate-100"}`}
                      key={message.id}
                    >
                      <p className="whitespace-pre-wrap text-sm">
                        {message.body}
                      </p>
                      <p
                        className={`mt-2 text-xs ${mine ? "text-blue-200" : "text-slate-500"}`}
                      >
                        {mine ? "You" : message.sender_email} ·{" "}
                        {new Date(message.created_at).toLocaleString()}
                      </p>
                    </article>
                  );
                })}
              </div>
              <form className="border-t pt-4" onSubmit={reply}>
                <label className="text-sm font-bold">
                  Direct response
                  <textarea
                    className="mt-2 min-h-24 w-full rounded-xl border p-3"
                    maxLength={10000}
                    onChange={(e) => setReplyBody(e.target.value)}
                    placeholder="Add the next update or resolution…"
                    required
                    value={replyBody}
                  />
                </label>
                <button className="brand-button mt-3" disabled={sending}>
                  {sending ? "Sending…" : "Reply"}
                </button>
              </form>
            </>
          ) : (
            <div className="grid flex-1 place-content-center text-slate-500">
              Select or start a conversation.
            </div>
          )}
        </section>
      </div>
    </main>
  );
}
