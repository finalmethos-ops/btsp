import type { CurrentUser } from "./api";

export type HomeDestination = {
  href: string;
  label: string;
  ariaLabel: string;
};

export function homeDestination(user: CurrentUser): HomeDestination {
  if (user.login_context === "event") {
    return {
      href: "/events/calendar",
      label: "Event home",
      ariaLabel: "Return to event home",
    };
  }
  return {
    href: "/",
    label: "Command center",
    ariaLabel: "Return to the command center",
  };
}
