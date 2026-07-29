import { ManagedEvent } from "./event-admin-api";

export type ArchivedStatusFilter = "all" | "completed" | "cancelled";

type ArchivedEventRecord = Pick<
  ManagedEvent,
  "name" | "venue_name" | "city" | "state_code" | "slug" | "status" | "ends_at"
>;

export function archivedEventYears(events: ArchivedEventRecord[]) {
  return Array.from(
    new Set(events.map((event) => new Date(event.ends_at).getFullYear())),
  ).sort((left, right) => right - left);
}

export function filterArchivedEvents<T extends ArchivedEventRecord>(
  events: T[],
  filters: {
    search: string;
    status: ArchivedStatusFilter;
    year: string;
  },
) {
  const query = filters.search.trim().toLocaleLowerCase();
  return events.filter((event) => {
    if (filters.status !== "all" && event.status !== filters.status)
      return false;
    if (
      filters.year !== "all" &&
      String(new Date(event.ends_at).getFullYear()) !== filters.year
    )
      return false;
    if (!query) return true;
    return [
      event.name,
      event.venue_name,
      event.city,
      event.state_code,
      event.slug,
    ].some((value) => value.toLocaleLowerCase().includes(query));
  });
}
