"use client";

import { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import {
  VendorHallBooth,
  VendorHallDirectory,
  VendorHallDirectoryBooth,
  VendorHallFloorMapStatus,
} from "@/lib/vendor-hall-api";
import { orderBoothVisitGroups } from "@/lib/vendor-hall-map";

type MapBooth = VendorHallBooth | VendorHallDirectoryBooth;

const statusStyles: Record<string, { label: string; className: string }> = {
  draft: {
    label: "Not submitted",
    className: "vendor-hall-status-draft",
  },
  inventory_submitted: {
    label: "Submitted",
    className: "vendor-hall-status-submitted",
  },
  ready_for_inspection: {
    label: "Ready for inspection",
    className: "vendor-hall-status-ready",
  },
  checkin_in_progress: {
    label: "Inspection in progress",
    className: "vendor-hall-status-checking",
  },
  fully_checked_in: {
    label: "Complete",
    className: "vendor-hall-status-complete",
  },
  exceptions_present: {
    label: "Exceptions",
    className: "vendor-hall-status-exception",
  },
  admin_reviewed: {
    label: "Reviewed",
    className: "vendor-hall-status-reviewed",
  },
  closed: {
    label: "Closed",
    className: "vendor-hall-status-closed",
  },
};

function numeric(value: string | null, fallback: number) {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : fallback;
}

function positioned(booth: MapBooth) {
  return booth.map_x !== null && booth.map_y !== null;
}

function boothStyle(booth: MapBooth) {
  const width = Math.max(2.5, Math.min(40, numeric(booth.map_width, 7)));
  const height = Math.max(4, Math.min(80, numeric(booth.map_height, 9)));
  // Keep the border inside the map wall as well as the booth center. The
  // inset accounts for the stage border and fractional percentage rounding.
  const left = Math.max(
    width / 2 + 0.5,
    Math.min(99.5 - width / 2, numeric(booth.map_x, 0)),
  );
  const top = Math.max(
    height / 2 + 0.5,
    Math.min(99.5 - height / 2, numeric(booth.map_y, 0)),
  );
  return {
    height: `${height}%`,
    left: `${left}%`,
    top: `${top}%`,
    width: `${width}%`,
    transform: "translate(-50%, -50%)",
  };
}

function positionedGroups(booths: MapBooth[]) {
  return Object.values(
    booths.reduce<Record<string, MapBooth[]>>((groups, booth) => {
      const key = `${numeric(booth.map_x, 0).toFixed(3)}:${numeric(booth.map_y, 0).toFixed(3)}`;
      groups[key] = [...(groups[key] ?? []), booth];
      return groups;
    }, {}),
  );
}

function zoneGroups(booths: MapBooth[]) {
  return booths.reduce<Record<string, MapBooth[]>>((groups, booth) => {
    const zone = booth.floor_map_zone || "Unassigned";
    groups[zone] = [...(groups[zone] ?? []), booth];
    return groups;
  }, {});
}

function uniqueValues(values: Array<string | null | undefined>) {
  return [
    ...new Set(values.filter((value): value is string => Boolean(value))),
  ];
}

export function VendorHallLiveMap({
  mapStatus,
  directoryMode = false,
  boothActions = {},
  onToggleSaved,
  onToggleVisited,
  onContactRepresentatives,
  allowContactRepresentatives = true,
  hideDirectoryTools = false,
  offlineReadOnly = false,
  onPlace,
  placementBoothId,
  sourceUrl,
  highlightedBoothIds = [],
  activeBoothId,
}: {
  mapStatus: VendorHallFloorMapStatus | VendorHallDirectory | null;
  directoryMode?: boolean;
  boothActions?: Record<string, { inventory: boolean; loadout: boolean }>;
  onToggleSaved?: (boothIds: string[], shouldSave: boolean) => Promise<void>;
  onToggleVisited?: (boothIds: string[], visited: boolean) => Promise<void>;
  onContactRepresentatives?: (boothIds: string[], label: string) => void;
  allowContactRepresentatives?: boolean;
  hideDirectoryTools?: boolean;
  offlineReadOnly?: boolean;
  onPlace?: (x: number, y: number) => void;
  placementBoothId?: string | null;
  sourceUrl?: string | null;
  highlightedBoothIds?: string[];
  activeBoothId?: string | null;
}) {
  const [selectedMapGroup, setSelectedMapGroup] = useState<string | null>(null);
  const [directoryQuery, setDirectoryQuery] = useState("");
  const [savedOnly, setSavedOnly] = useState(false);
  const [savingGroup, setSavingGroup] = useState<string | null>(null);
  const [visitingGroup, setVisitingGroup] = useState<string | null>(null);
  const [mapZoom, setMapZoom] = useState(1);
  const [directoryView, setDirectoryView] = useState<"map" | "list">("map");
  const [hoveredMapGroup, setHoveredMapGroup] = useState<string | null>(null);
  const [popoverPosition, setPopoverPosition] = useState<{
    left: number;
    maxHeight: number;
    top: number;
    placement: "above" | "below";
  } | null>(null);
  const mapScrollRef = useRef<HTMLDivElement>(null);
  const autoFitEventRef = useRef<string | null>(null);
  const boothElementRefs = useRef(new Map<string, HTMLElement>());
  const booths = mapStatus?.booths ?? [];
  const positionedBooths = booths.filter(positioned);
  const mapGroups = positionedGroups(positionedBooths);
  const unpositionedBooths = booths.filter((booth) => !positioned(booth));
  const grouped = zoneGroups(unpositionedBooths);
  const query = directoryQuery.trim().toLowerCase();
  const matchingMapGroups = mapGroups.filter(
    (group) =>
      (!savedOnly ||
        group.some((booth) => "is_saved" in booth && booth.is_saved)) &&
      (!query ||
        group.some((booth) =>
          [
            booth.vendor_name,
            booth.booth_name,
            booth.booth_number,
            booth.floor_map_zone,
            ...("attendees" in booth ? booth.attendees : []),
          ]
            .filter(Boolean)
            .some((value) => value?.toLowerCase().includes(query)),
        )),
  );
  const entryways = Array.isArray(mapStatus?.floor_map?.layout_json.entryways)
    ? mapStatus.floor_map.layout_json.entryways
    : [];
  const firstEntryway = entryways[0] as { x?: number } | undefined;
  const savedMapGroups = mapGroups.filter((group) =>
    group.some((booth) => "is_saved" in booth && booth.is_saved),
  );
  const visitedGroupCount = savedMapGroups.filter((group) =>
    group.every((booth) => "is_visited" in booth && booth.is_visited),
  ).length;
  const savedVisitGroups = orderBoothVisitGroups(
    savedMapGroups.filter(
      (group) =>
        !group.every((booth) => "is_visited" in booth && booth.is_visited),
    ),
    { x: firstEntryway?.x ?? 50, y: 100 },
  );
  const visiblePopoverGroupKey = selectedMapGroup ?? hoveredMapGroup;
  const visiblePopoverGroup =
    mapGroups.find(
      (group) =>
        group.map((item) => item.id).join(":") === visiblePopoverGroupKey,
    ) ?? null;

  useEffect(() => {
    if (!visiblePopoverGroupKey) {
      setPopoverPosition(null);
      return;
    }
    const updatePosition = () => {
      const boothElement = boothElementRefs.current.get(visiblePopoverGroupKey);
      if (!boothElement) {
        setPopoverPosition(null);
        return;
      }
      const bounds = boothElement.getBoundingClientRect();
      const cardWidth = Math.min(320, Math.max(220, window.innerWidth - 24));
      const horizontalCenter = bounds.left + bounds.width / 2;
      const left = Math.min(
        window.innerWidth - cardWidth / 2 - 12,
        Math.max(cardWidth / 2 + 12, horizontalCenter),
      );
      const roomBelow = window.innerHeight - bounds.bottom;
      const roomAbove = bounds.top;
      const placement =
        roomBelow < 360 && roomAbove > roomBelow ? "above" : "below";
      const availableHeight =
        placement === "above" ? roomAbove - 20 : roomBelow - 20;
      setPopoverPosition({
        left,
        maxHeight: Math.max(120, Math.min(520, availableHeight)),
        top: placement === "above" ? bounds.top - 8 : bounds.bottom + 8,
        placement,
      });
    };
    updatePosition();
    window.addEventListener("resize", updatePosition);
    window.addEventListener("scroll", updatePosition, true);
    return () => {
      window.removeEventListener("resize", updatePosition);
      window.removeEventListener("scroll", updatePosition, true);
    };
  }, [mapZoom, visiblePopoverGroupKey]);

  useEffect(() => {
    const container = mapScrollRef.current;
    const eventKey = mapStatus?.event_id ?? "vendor-hall-map";
    if (
      !container ||
      directoryView === "list" ||
      autoFitEventRef.current === eventKey
    ) {
      return;
    }
    autoFitEventRef.current = eventKey;
    if (container.clientWidth <= 760) {
      setMapZoom(
        Math.max(0.3, Math.min(1, (container.clientWidth - 24) / 1080)),
      );
      container.scrollTo({ left: 0 });
    }
  }, [directoryView, mapStatus?.event_id]);

  function selectDirectoryGroup(group: MapBooth[]) {
    const key = group.map((item) => item.id).join(":");
    setSelectedMapGroup(key);
    const container = mapScrollRef.current;
    if (!container) return;
    const x = numeric(group[0].map_x, 50) / 100;
    window.requestAnimationFrame(() => {
      container.scrollTo({
        behavior: "smooth",
        left: Math.max(
          0,
          x * container.scrollWidth - container.clientWidth / 2,
        ),
      });
    });
  }

  function fitMap() {
    const width = mapScrollRef.current?.clientWidth ?? 1080;
    setMapZoom(Math.max(0.3, Math.min(1, (width - 24) / 1080)));
    mapScrollRef.current?.scrollTo({ behavior: "smooth", left: 0 });
  }

  function groupDetails(group: MapBooth[]) {
    const boothNumbers = uniqueValues(group.map((item) => item.booth_number));
    const vendorNames = uniqueValues(
      group.map((item) => item.vendor_name ?? item.booth_name),
    );
    const attendees = uniqueValues(
      group.flatMap((item) => ("attendees" in item ? item.attendees : [])),
    );
    const representativeBoothIds = group
      .filter((item) => "attendees" in item && item.attendees.length > 0)
      .map((item) => item.id);
    const assignedActions = group.reduce(
      (current, item) => ({
        inventory:
          current.inventory || Boolean(boothActions[item.id]?.inventory),
        loadout: current.loadout || Boolean(boothActions[item.id]?.loadout),
      }),
      { inventory: false, loadout: false },
    );
    const groupKey = group.map((item) => item.id).join(":");
    const groupIsSaved = group.some(
      (item) => "is_saved" in item && item.is_saved,
    );
    const groupIsVisited = group.every(
      (item) => "is_visited" in item && item.is_visited,
    );
    return {
      assignedActions,
      attendees,
      boothLabel: boothNumbers.join(" / ") || "TBD",
      boothNumbers,
      groupIsSaved,
      groupIsVisited,
      groupKey,
      representativeBoothIds,
      vendorLabel:
        vendorNames.join(" / ") ||
        group.map((item) => item.booth_name).join(" / "),
      vendorNames,
    };
  }

  function renderDirectoryActions(group: MapBooth[]) {
    const {
      assignedActions,
      groupIsSaved,
      groupIsVisited,
      groupKey,
      representativeBoothIds,
      vendorLabel,
    } = groupDetails(group);
    return (
      <div className="vendor-hall-directory-actions">
        {assignedActions.inventory ? (
          <a href="#assigned-vendor-hall-work">Open assigned booth work</a>
        ) : null}
        {assignedActions.loadout ? (
          <a href="#assigned-loadout-work">Open loadout checklist</a>
        ) : null}
        {directoryMode && onToggleSaved && !offlineReadOnly ? (
          <button
            className="vendor-hall-save-booth"
            disabled={savingGroup === groupKey}
            onClick={(event) => {
              event.stopPropagation();
              setSavingGroup(groupKey);
              void onToggleSaved(
                group.map((item) => item.id),
                !groupIsSaved,
              ).finally(() => setSavingGroup(null));
            }}
            type="button"
          >
            {savingGroup === groupKey
              ? "Saving..."
              : groupIsSaved
                ? "Remove from my booths"
                : "Add to my booths"}
          </button>
        ) : null}
        {directoryMode &&
        groupIsSaved &&
        onToggleVisited &&
        !offlineReadOnly ? (
          <button
            className="vendor-hall-visit-booth"
            disabled={visitingGroup === groupKey}
            onClick={(event) => {
              event.stopPropagation();
              setVisitingGroup(groupKey);
              void onToggleVisited(
                group.map((item) => item.id),
                !groupIsVisited,
              ).finally(() => setVisitingGroup(null));
            }}
            type="button"
          >
            {visitingGroup === groupKey
              ? "Updating..."
              : groupIsVisited
                ? "Mark not visited"
                : "Mark visited"}
          </button>
        ) : null}
        {directoryMode &&
        representativeBoothIds.length &&
        onContactRepresentatives &&
        allowContactRepresentatives &&
        !offlineReadOnly ? (
          <button
            className="vendor-hall-contact-booth"
            onClick={(event) => {
              event.stopPropagation();
              onContactRepresentatives(representativeBoothIds, vendorLabel);
            }}
            type="button"
          >
            Request a meeting
          </button>
        ) : null}
      </div>
    );
  }

  function renderFloatingPopover(group: MapBooth[]) {
    const booth = group[0];
    const status =
      "status" in booth
        ? (statusStyles[booth.status] ?? statusStyles.draft)
        : statusStyles.draft;
    const { boothLabel, groupKey, vendorLabel } = groupDetails(group);
    const inventoryCount = group.reduce(
      (total, item) =>
        total + ("inventory_count" in item ? item.inventory_count : 0),
      0,
    );
    const exceptionsCount = group.reduce(
      (total, item) =>
        total + ("exceptions_count" in item ? item.exceptions_count : 0),
      0,
    );
    const attendees = uniqueValues(
      group.flatMap((item) => ("attendees" in item ? item.attendees : [])),
    );
    if (!popoverPosition || typeof document === "undefined") return null;
    return createPortal(
      <div
        className={`vendor-hall-booth-popover vendor-hall-booth-popover-floating is-${popoverPosition.placement}`}
        onClick={(event) => event.stopPropagation()}
        onMouseEnter={() => setSelectedMapGroup(groupKey)}
        onMouseLeave={() => setHoveredMapGroup(null)}
        style={{
          left: popoverPosition.left,
          maxHeight: popoverPosition.maxHeight,
          top: popoverPosition.top,
        }}
      >
        <button
          aria-label="Close booth information"
          className="vendor-hall-popover-close"
          onClick={() => {
            setSelectedMapGroup(null);
            setHoveredMapGroup(null);
          }}
          type="button"
        >
          ×
        </button>
        <b>{vendorLabel}</b>
        <span>Booth {boothLabel}</span>
        {!directoryMode ? <span>{status.label}</span> : null}
        {!directoryMode ? (
          <small>
            {inventoryCount} items · {exceptionsCount} exceptions
          </small>
        ) : null}
        {directoryMode ? (
          <small>
            {attendees.length
              ? `Representatives: ${attendees.join(", ")}`
              : "No vendor representatives listed"}
          </small>
        ) : null}
        {directoryMode && !hideDirectoryTools
          ? renderDirectoryActions(group)
          : null}
      </div>,
      document.body,
    );
  }

  return (
    <div className="event-ui vendor-hall-live-map">
      {!directoryMode ? (
        <div className="vendor-hall-live-map-header">
          <div>
            <p className="brand-eyebrow">Live status board</p>
            <h3>{mapStatus?.floor_map?.name ?? "Vendor hall floor map"}</h3>
            <p>
              {positionedBooths.length} positioned · {unpositionedBooths.length}{" "}
              unpositioned · {booths.length} total booths
            </p>
          </div>
          <div className="vendor-hall-map-legend">
            {Object.entries(statusStyles).map(([status, style]) => (
              <span key={status}>
                <i className={style.className} />
                {style.label}
              </span>
            ))}
          </div>
        </div>
      ) : null}
      {directoryMode && !hideDirectoryTools ? (
        <div className="vendor-hall-directory-search">
          <div className="vendor-hall-directory-search-header">
            <label
              htmlFor={`vendor-hall-search-${mapStatus?.event_id ?? "map"}`}
            >
              Find a vendor, booth, or representative
            </label>
            <div
              aria-label="Directory view"
              className="vendor-hall-directory-view-toggle"
            >
              {(["map", "list"] as const).map((view) => (
                <button
                  aria-pressed={directoryView === view}
                  className={directoryView === view ? "is-active" : ""}
                  key={view}
                  onClick={() => setDirectoryView(view)}
                  type="button"
                >
                  {view === "map" ? "Map" : "List"}
                </button>
              ))}
            </div>
          </div>
          <input
            id={`vendor-hall-search-${mapStatus?.event_id ?? "map"}`}
            onChange={(event) => {
              setDirectoryQuery(event.target.value);
              setSelectedMapGroup(null);
            }}
            placeholder="Search vendor, booth number, or attendee name"
            type="search"
            value={directoryQuery}
          />
          <button
            aria-pressed={savedOnly}
            className={`vendor-hall-saved-filter ${savedOnly ? "is-active" : ""}`}
            onClick={() => {
              setSavedOnly((current) => !current);
              setSelectedMapGroup(null);
            }}
            type="button"
          >
            {savedOnly ? "Showing my booths" : "Show my booths to visit"}
          </button>
          {query || savedOnly ? (
            <div className="vendor-hall-directory-results">
              {matchingMapGroups.length ? (
                matchingMapGroups.map((group) => (
                  <button
                    key={group.map((item) => item.id).join(":")}
                    onClick={() => selectDirectoryGroup(group)}
                    type="button"
                  >
                    <strong>
                      {group
                        .map((item) => item.vendor_name ?? item.booth_name)
                        .filter(
                          (value, index, values) =>
                            values.indexOf(value) === index,
                        )
                        .join(" / ")}
                    </strong>
                    <span>
                      Booth {group.map((item) => item.booth_number).join(" / ")}
                    </span>
                  </button>
                ))
              ) : (
                <span>No matching positioned booths</span>
              )}
            </div>
          ) : null}
        </div>
      ) : null}
      {highlightedBoothIds.length ? (
        <div className="vendor-hall-loadout-legend">
          <span>
            <i className="is-assigned" /> Assigned inventory booth
          </span>
          <span>
            <i className="is-active" /> Selected product booth
          </span>
        </div>
      ) : null}
      {directoryMode && !hideDirectoryTools && directoryView === "list" ? (
        <div className="vendor-hall-directory-list">
          {matchingMapGroups.map((group) => {
            const {
              attendees,
              boothLabel,
              groupIsSaved,
              groupIsVisited,
              groupKey,
              vendorLabel,
            } = groupDetails(group);
            return (
              <article
                className={`vendor-hall-directory-card ${
                  selectedMapGroup === groupKey ? "is-selected" : ""
                }`}
                key={groupKey}
                ref={(element) => {
                  if (element) boothElementRefs.current.set(groupKey, element);
                  else boothElementRefs.current.delete(groupKey);
                }}
                onMouseEnter={() => setHoveredMapGroup(groupKey)}
                onMouseLeave={() => setHoveredMapGroup(null)}
              >
                <button
                  aria-pressed={selectedMapGroup === groupKey}
                  onClick={() => selectDirectoryGroup(group)}
                  type="button"
                >
                  <span>
                    <strong>{vendorLabel}</strong>
                    <small>Booth {boothLabel}</small>
                  </span>
                  <span className="vendor-hall-directory-card-flags">
                    {groupIsSaved ? <i>Saved</i> : null}
                    {groupIsVisited ? <i>Visited</i> : null}
                  </span>
                </button>
                {attendees.length ? (
                  <p>Representatives: {attendees.join(", ")}</p>
                ) : (
                  <p>No vendor representatives listed.</p>
                )}
                {renderDirectoryActions(group)}
              </article>
            );
          })}
          {!matchingMapGroups.length ? (
            <p className="vendor-hall-directory-empty">
              No matching positioned booths.
            </p>
          ) : null}
        </div>
      ) : null}
      {directoryMode && !hideDirectoryTools && savedVisitGroups.length ? (
        <div className="vendor-hall-visit-route">
          <div>
            <strong>My suggested booth route</strong>
            <span>Starts at the mapped entrance and reduces backtracking.</span>
            <span>
              {visitedGroupCount} of {savedMapGroups.length} stops visited ·{" "}
              {savedVisitGroups.length} remaining
            </span>
          </div>
          <ol>
            {savedVisitGroups.map((group) => (
              <li key={group.map((item) => item.id).join(":")}>
                <button
                  onClick={() => selectDirectoryGroup(group)}
                  type="button"
                >
                  <strong>
                    {group
                      .map((item) => item.vendor_name ?? item.booth_name)
                      .filter(
                        (value, index, values) =>
                          values.indexOf(value) === index,
                      )
                      .join(" / ")}
                  </strong>
                  <span>
                    Booth {group.map((item) => item.booth_number).join(" / ")}
                  </span>
                </button>
              </li>
            ))}
          </ol>
        </div>
      ) : null}
      <div
        className={`vendor-hall-map-zoom ${hideDirectoryTools || directoryView === "list" ? "is-list-hidden" : ""}`}
        aria-label="Map zoom controls"
      >
        <button
          aria-label="Zoom map out"
          disabled={mapZoom <= 0.3}
          onClick={() => setMapZoom((current) => Math.max(0.3, current - 0.15))}
          type="button"
        >
          −
        </button>
        <span>{Math.round(mapZoom * 100)}%</span>
        <button
          aria-label="Zoom map in"
          disabled={mapZoom >= 1.6}
          onClick={() => setMapZoom((current) => Math.min(1.6, current + 0.15))}
          type="button"
        >
          +
        </button>
        <button onClick={fitMap} type="button">
          Fit map
        </button>
      </div>
      <div
        className={`vendor-hall-map-scroll ${directoryMode && directoryView === "list" ? "is-list-hidden" : ""}`}
        ref={mapScrollRef}
      >
        <div
          className={`vendor-hall-map-stage ${placementBoothId ? "is-placing" : ""}`}
          style={{
            aspectRatio: String(
              mapStatus?.floor_map?.layout_json.page_aspect_ratio ?? 1.55,
            ),
            minWidth: `${1080 * mapZoom}px`,
            width: `${1080 * mapZoom}px`,
          }}
          aria-label="Vendor hall map"
          onClick={(event) => {
            if (!placementBoothId || !onPlace) return;
            const bounds = event.currentTarget.getBoundingClientRect();
            onPlace(
              Math.max(
                0,
                Math.min(
                  100,
                  ((event.clientX - bounds.left) / bounds.width) * 100,
                ),
              ),
              Math.max(
                0,
                Math.min(
                  100,
                  ((event.clientY - bounds.top) / bounds.height) * 100,
                ),
              ),
            );
          }}
        >
          {sourceUrl ? (
            <object
              aria-label="Imported vendor hall floor plan"
              className="vendor-hall-map-pdf"
              data={sourceUrl}
              type="image/png"
            />
          ) : null}
          <div className="vendor-hall-map-grid" />
          {entryways.map((entry, index) => {
            const item = entry as { label?: string; x?: number };
            return (
              <span
                className="vendor-hall-entryway"
                key={`${item.x}-${index}`}
                style={{ left: `${item.x ?? 50}%` }}
              >
                {item.label ?? "ENTRY"}
              </span>
            );
          })}
          {mapGroups.map((group) => {
            const booth = group[0];
            const status =
              "status" in booth
                ? (statusStyles[booth.status] ?? statusStyles.draft)
                : statusStyles.draft;
            const {
              boothNumbers,
              groupIsSaved,
              groupIsVisited,
              groupKey,
              vendorNames,
            } = groupDetails(group);
            const matchesQuery = matchingMapGroups.some(
              (item) => item === group,
            );
            const routeIndex = savedVisitGroups.findIndex(
              (item) => item === group,
            );
            const groupIsHighlighted = group.some((item) =>
              highlightedBoothIds.includes(item.id),
            );
            const groupIsActive = group.some(
              (item) => item.id === activeBoothId,
            );
            const mapX = numeric(booth.map_x, 50);
            const mapY = numeric(booth.map_y, 50);
            const detailPlacement = [
              mapY > 62 ? "opens-up" : "opens-down",
              mapX < 14
                ? "aligns-left"
                : mapX > 86
                  ? "aligns-right"
                  : "aligns-center",
            ].join(" ");
            return (
              <article
                aria-expanded={selectedMapGroup === groupKey}
                aria-label={`${vendorNames.join(" / ")}, booth ${boothNumbers.join(" / ") || "to be determined"}${routeIndex >= 0 ? `, route stop ${routeIndex + 1}` : ""}${groupIsVisited ? ", visited" : ""}`}
                className={`vendor-hall-map-booth ${directoryMode ? "vendor-hall-status-submitted" : status.className} ${detailPlacement} ${selectedMapGroup === groupKey ? "is-detail-open" : ""} ${directoryMode && (query || savedOnly) && !matchesQuery ? "is-search-dimmed" : ""} ${highlightedBoothIds.length && !groupIsHighlighted ? "is-loadout-dimmed" : ""} ${groupIsHighlighted ? "is-loadout-assigned" : ""} ${groupIsActive ? "is-loadout-active" : ""} ${groupIsSaved ? "is-saved" : ""} ${groupIsVisited ? "is-visited" : ""} ${routeIndex >= 0 ? "is-route-stop" : ""}`}
                key={groupKey}
                ref={(element) => {
                  if (element) {
                    boothElementRefs.current.set(groupKey, element);
                  } else {
                    boothElementRefs.current.delete(groupKey);
                  }
                }}
                onKeyDown={(event) => {
                  if (
                    event.target === event.currentTarget &&
                    (event.key === "Enter" || event.key === " ")
                  ) {
                    event.preventDefault();
                    setSelectedMapGroup((current) =>
                      current === groupKey ? null : groupKey,
                    );
                  }
                }}
                onClick={(event) => {
                  event.stopPropagation();
                  setSelectedMapGroup((current) =>
                    current === groupKey ? null : groupKey,
                  );
                }}
                onMouseEnter={() => setHoveredMapGroup(groupKey)}
                onMouseLeave={() => {
                  window.setTimeout(() => {
                    setHoveredMapGroup((current) =>
                      current === groupKey ? null : current,
                    );
                  }, 180);
                }}
                role="button"
                style={boothStyle(booth)}
                tabIndex={0}
                title={`${vendorNames.join(" / ")}${directoryMode ? "" : ` · ${status.label}`}`}
              >
                {routeIndex >= 0 ? (
                  <span aria-hidden="true" className="vendor-hall-route-number">
                    {routeIndex + 1}
                  </span>
                ) : null}
                <strong>
                  {boothNumbers.join(" / ") ||
                    group.map((item) => item.booth_name).join(" / ")}
                </strong>
              </article>
            );
          })}
          {!positionedBooths.length ? (
            <div className="vendor-hall-map-empty">
              <strong>No positioned booths yet</strong>
              <span>
                Select a booth above, then click its location on the PDF.
              </span>
            </div>
          ) : null}
        </div>
      </div>
      {visiblePopoverGroup ? renderFloatingPopover(visiblePopoverGroup) : null}
      {unpositionedBooths.length ? (
        <div className="vendor-hall-zone-fallback">
          {Object.entries(grouped).map(([zone, zoneBooths]) => (
            <section key={zone}>
              <h4>{zone}</h4>
              <div>
                {zoneBooths.map((booth) => {
                  const status =
                    "status" in booth
                      ? (statusStyles[booth.status] ?? statusStyles.draft)
                      : statusStyles.draft;
                  return (
                    <span
                      className={
                        directoryMode
                          ? "vendor-hall-status-submitted"
                          : status.className
                      }
                      key={booth.id}
                    >
                      {booth.booth_number || booth.booth_name} ·{" "}
                      {booth.vendor_name ?? booth.booth_name}
                    </span>
                  );
                })}
              </div>
            </section>
          ))}
        </div>
      ) : null}
    </div>
  );
}
