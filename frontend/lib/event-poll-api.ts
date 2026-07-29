import { apiFetch } from "./api";

export type EventPollOption = {
  id: string;
  position: number;
  label: string;
  vote_count: number;
  percentage: number;
};

export type EventPoll = {
  id: string;
  event_id: string;
  sub_event_id: string;
  slide_id: string | null;
  question: string;
  status: "draft" | "open" | "closed";
  show_results: boolean;
  total_votes: number;
  selected_option_id: string | null;
  options: EventPollOption[];
  created_at: string;
  opened_at: string | null;
  closed_at: string | null;
};

export const listEventPolls = (subEventId: string) =>
  apiFetch<EventPoll[]>(`/event-polls/sub-events/${subEventId}`);

export const createEventPoll = (
  subEventId: string,
  payload: {
    question: string;
    options: string[];
    slide_id?: string | null;
    show_results: boolean;
  },
) =>
  apiFetch<EventPoll>(`/event-polls/sub-events/${subEventId}`, {
    method: "POST",
    body: JSON.stringify(payload),
  });

export const setEventPollStatus = (pollId: string, status: "open" | "closed") =>
  apiFetch<EventPoll>(`/event-polls/${pollId}/status`, {
    method: "PUT",
    body: JSON.stringify({ status }),
  });

export const getActiveEventPoll = (subEventId: string) =>
  apiFetch<EventPoll | null>(`/event-polls/active/${subEventId}`);

export const voteInEventPoll = (pollId: string, optionId: string) =>
  apiFetch<EventPoll>(`/event-polls/${pollId}/vote`, {
    method: "POST",
    body: JSON.stringify({ option_id: optionId }),
  });
