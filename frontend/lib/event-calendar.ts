import { EventCalendarEntry } from "./event-calendar-api";

export type CalendarEntryTiming = "past" | "live" | "upcoming";

export function calendarEntryTiming(
  entry: Pick<EventCalendarEntry, "starts_at" | "ends_at">,
  now = new Date(),
): CalendarEntryTiming {
  const timestamp = now.getTime();
  if (timestamp >= new Date(entry.ends_at).getTime()) return "past";
  if (timestamp >= new Date(entry.starts_at).getTime()) return "live";
  return "upcoming";
}

function escapeIcs(value: string) {
  return value
    .replaceAll("\\", "\\\\")
    .replaceAll("\n", "\\n")
    .replaceAll(",", "\\,")
    .replaceAll(";", "\\;");
}

function icsTimestamp(value: string | Date) {
  return new Date(value)
    .toISOString()
    .replaceAll("-", "")
    .replaceAll(":", "")
    .replace(/\.\d{3}Z$/, "Z");
}

export function eventCalendarIcs(
  entries: EventCalendarEntry[],
  generatedAt = new Date(),
) {
  const stamp = icsTimestamp(generatedAt);
  const events = entries.flatMap((entry) => [
    "BEGIN:VEVENT",
    `UID:${escapeIcs(`${entry.id}@btsp.events`)}`,
    `DTSTAMP:${stamp}`,
    `DTSTART:${icsTimestamp(entry.starts_at)}`,
    `DTEND:${icsTimestamp(entry.ends_at)}`,
    `SUMMARY:${escapeIcs(entry.title)}`,
    `DESCRIPTION:${escapeIcs(entry.description ?? "")}`,
    `LOCATION:${escapeIcs(entry.location ?? "")}`,
    "END:VEVENT",
  ]);
  return [
    "BEGIN:VCALENDAR",
    "VERSION:2.0",
    "PRODID:-//BTSP//Event Schedule//EN",
    "CALSCALE:GREGORIAN",
    "METHOD:PUBLISH",
    ...events,
    "END:VCALENDAR",
    "",
  ].join("\r\n");
}

export function eventCalendarFilename(eventName: string) {
  const safeName = eventName
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-|-$/g, "");
  return `${safeName || "btsp-event"}-schedule.ics`;
}
