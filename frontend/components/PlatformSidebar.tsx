"use client";

import Image from "next/image";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import { useAuth } from "@/lib/auth";
import {
  PlatformNavigationGroup,
  platformNavigationGroups,
  visiblePlatformNavigation,
} from "@/lib/platform-navigation";

function selected(pathname: string, href: string) {
  if (href === "/") return pathname === "/";
  return pathname === href || pathname.startsWith(`${href}/`);
}

export function PlatformSidebar() {
  const { user } = useAuth();
  const pathname = usePathname();
  const navigation = visiblePlatformNavigation(user);
  const activeGroup = navigation.find((item) =>
    selected(pathname, item.href),
  )?.group;
  const [openGroups, setOpenGroups] = useState<Set<PlatformNavigationGroup>>(
    () => new Set(activeGroup ? [activeGroup] : []),
  );
  const grouped = useMemo(
    () =>
      platformNavigationGroups.map((group) => ({
        group,
        items: navigation.filter((item) => item.group === group),
      })),
    [navigation],
  );

  useEffect(() => {
    if (!activeGroup) return;
    setOpenGroups((current) => new Set(current).add(activeGroup));
  }, [activeGroup]);

  function toggle(group: PlatformNavigationGroup) {
    setOpenGroups((current) => {
      const next = new Set(current);
      if (next.has(group)) next.delete(group);
      else next.add(group);
      return next;
    });
  }

  return (
    <aside className="brand-sidebar platform-sidebar">
      <div className="sidebar-branding">
        <Image
          alt="Purchasing Intelligence branding"
          fill
          sizes="245px"
          src="/brand/purchasing-intelligence-short.png"
        />
      </div>
      <nav className="brand-nav" aria-label="Platform navigation">
        {navigation
          .filter((item) => !item.group)
          .map((item) => (
            <Link
              className={selected(pathname, item.href) ? "is-selected" : ""}
              href={item.href}
              key={item.href}
            >
              {item.label}
            </Link>
          ))}
        {grouped.map(({ group, items }) =>
          items.length ? (
            <section className="platform-nav-group" key={group}>
              <button
                aria-expanded={openGroups.has(group)}
                className="platform-nav-group-toggle"
                onClick={() => toggle(group)}
                type="button"
              >
                <span>{group}</span>
                <span aria-hidden="true">
                  {openGroups.has(group) ? "−" : "+"}
                </span>
              </button>
              {openGroups.has(group) ? (
                <div className="platform-nav-group-links">
                  {items.map((item) => (
                    <Link
                      className={
                        selected(pathname, item.href) ? "is-selected" : ""
                      }
                      href={item.href}
                      key={item.href}
                    >
                      {item.label}
                    </Link>
                  ))}
                </div>
              ) : null}
            </section>
          ) : null,
        )}
      </nav>
    </aside>
  );
}
