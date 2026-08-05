"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { ManagedSubEvent } from "@/lib/event-admin-api";
import {
  checkInEventPass,
  EventAttendanceRoster,
  getEventAttendance,
  setEventAttendance,
} from "@/lib/event-attendance-api";
import { subscribeEventRealtime } from "@/lib/event-realtime";

type DetectedBarcode = { rawValue: string };
type BarcodeDetectorInstance = {
  detect(source: HTMLVideoElement): Promise<DetectedBarcode[]>;
};
type BarcodeDetectorConstructor = new (options: {
  formats: string[];
}) => BarcodeDetectorInstance;

export function EventAttendancePanel({
  subEvents,
}: {
  subEvents: ManagedSubEvent[];
}) {
  const [subEventId, setSubEventId] = useState(subEvents[0]?.id ?? "");
  const [roster, setRoster] = useState<EventAttendanceRoster | null>(null);
  const [query, setQuery] = useState("");
  const [passCode, setPassCode] = useState("");
  const [scanMessage, setScanMessage] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [scanBusy, setScanBusy] = useState(false);
  const [cameraActive, setCameraActive] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const videoRef = useRef<HTMLVideoElement>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const scanFrameRef = useRef<number | null>(null);

  const stopCamera = useCallback(() => {
    if (scanFrameRef.current !== null) {
      window.cancelAnimationFrame(scanFrameRef.current);
      scanFrameRef.current = null;
    }
    streamRef.current?.getTracks().forEach((track) => track.stop());
    streamRef.current = null;
    setCameraActive(false);
  }, []);

  useEffect(() => stopCamera, [stopCamera]);

  async function startCamera() {
    setError(null);
    const Detector = (
      window as typeof window & {
        BarcodeDetector?: BarcodeDetectorConstructor;
      }
    ).BarcodeDetector;
    if (!Detector || !navigator.mediaDevices?.getUserMedia) {
      setError(
        "Camera QR scanning is not supported in this browser. Enter the pass code manually.",
      );
      return;
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: { ideal: "environment" } },
        audio: false,
      });
      streamRef.current = stream;
      setCameraActive(true);
      const video = videoRef.current;
      if (!video) {
        stopCamera();
        return;
      }
      video.srcObject = stream;
      await video.play();
      const detector = new Detector({ formats: ["qr_code"] });
      const detect = async () => {
        try {
          const result = await detector.detect(video);
          const code = result[0]?.rawValue?.trim();
          if (code) {
            setPassCode(code);
            setScanMessage(
              "Pass scanned. Select check in or check out to confirm.",
            );
            stopCamera();
            return;
          }
        } catch {
          // Individual frames can fail while the camera focuses; keep scanning.
        }
        scanFrameRef.current = window.requestAnimationFrame(
          () => void detect(),
        );
      };
      scanFrameRef.current = window.requestAnimationFrame(() => void detect());
    } catch {
      stopCamera();
      setError("Camera access was unavailable. Enter the pass code manually.");
    }
  }

  const refresh = useCallback(() => {
    if (!subEventId) return Promise.resolve();
    return getEventAttendance(subEventId).then(setRoster);
  }, [subEventId]);

  useEffect(() => {
    setRoster(null);
    void refresh().catch((caught: unknown) =>
      setError(
        caught instanceof Error ? caught.message : "Unable to load attendance.",
      ),
    );
    if (!subEventId) return;
    const timer = window.setInterval(() => void refresh(), 15_000);
    const unsubscribe = subscribeEventRealtime(
      subEventId,
      () => void refresh(),
    );
    return () => {
      window.clearInterval(timer);
      unsubscribe();
    };
  }, [refresh, subEventId]);

  const members = useMemo(() => {
    const needle = query.trim().toLowerCase();
    if (!needle) return roster?.members ?? [];
    return (roster?.members ?? []).filter((member) =>
      [
        member.display_name,
        member.email,
        member.vendor_code,
        member.entity_code,
      ]
        .filter(Boolean)
        .some((value) => value?.toLowerCase().includes(needle)),
    );
  }, [query, roster?.members]);

  async function update(
    memberId: string,
    status: "checked_in" | "checked_out",
  ) {
    setBusyId(memberId);
    setError(null);
    try {
      setRoster(await setEventAttendance(subEventId, memberId, status));
    } catch (caught) {
      setError(
        caught instanceof Error
          ? caught.message
          : "Unable to update attendance.",
      );
    } finally {
      setBusyId(null);
    }
  }

  async function scanPass(status: "checked_in" | "checked_out" = "checked_in") {
    const code = passCode.trim();
    if (!code) return;
    setScanBusy(true);
    setError(null);
    setScanMessage(null);
    try {
      const result = await checkInEventPass(subEventId, code, status);
      setRoster(result.roster);
      setPassCode("");
      setQuery(result.member.pass_code);
      setScanMessage(
        `${result.member.display_name} ${status === "checked_in" ? "checked in" : "checked out"}.`,
      );
    } catch (caught) {
      setError(
        caught instanceof Error
          ? caught.message
          : "Unable to process the pass.",
      );
    } finally {
      setScanBusy(false);
    }
  }

  return (
    <section className="event-ui rounded-2xl border bg-white p-5">
      <p className="brand-eyebrow">Onsite operations</p>
      <h3 className="text-xl font-bold">Registration and check-in</h3>
      {!subEvents.length ? (
        <p className="mt-3 text-slate-500">
          Add a sub-event to open its roster.
        </p>
      ) : (
        <>
          <div className="mt-4 grid gap-3 md:grid-cols-2">
            <label className="text-sm font-semibold">
              Sub-event
              <select
                className="mt-1 w-full rounded-lg border p-3"
                onChange={(event) => setSubEventId(event.target.value)}
                value={subEventId}
              >
                {subEvents.map((item) => (
                  <option key={item.id} value={item.id}>
                    {item.name}
                  </option>
                ))}
              </select>
            </label>
            <label className="text-sm font-semibold">
              Find attendee, vendor, or staff
              <input
                className="mt-1 w-full rounded-lg border p-3"
                onChange={(event) => setQuery(event.target.value)}
                placeholder="Name, email, entity, vendor"
                value={query}
              />
            </label>
          </div>
          <form
            className="mt-4 rounded-xl border bg-slate-50 p-4"
            onSubmit={(event) => {
              event.preventDefault();
              void scanPass("checked_in");
            }}
          >
            <p className="brand-eyebrow">Fast pass scan</p>
            <div className="mt-3 grid gap-3 md:grid-cols-[1fr_auto_auto_auto]">
              <input
                className="rounded-lg border p-3"
                onChange={(event) => setPassCode(event.target.value)}
                placeholder="Scan or enter pass code, e.g. BTSP-ABC12345"
                value={passCode}
              />
              <button
                className="rounded-lg bg-green-700 px-4 py-2 font-semibold text-white disabled:bg-slate-400"
                disabled={scanBusy || !passCode.trim()}
              >
                {scanBusy ? "Processing…" : "Check in"}
              </button>
              <button
                className="rounded-lg border px-4 py-2 font-semibold disabled:text-slate-400"
                disabled={scanBusy || !passCode.trim()}
                onClick={() => void scanPass("checked_out")}
                type="button"
              >
                Check out
              </button>
              <button
                className="rounded-lg border px-4 py-2 font-semibold disabled:text-slate-400"
                disabled={scanBusy}
                onClick={() =>
                  cameraActive ? stopCamera() : void startCamera()
                }
                type="button"
              >
                {cameraActive ? "Cancel camera" : "Scan QR"}
              </button>
            </div>
            <video
              aria-label="QR code camera preview"
              className={`${cameraActive ? "mt-3 block" : "hidden"} max-h-72 w-full rounded-xl bg-slate-950 object-cover`}
              muted
              playsInline
              ref={videoRef}
            />
            {scanMessage ? (
              <p className="mt-3 rounded-lg bg-green-50 p-3 text-green-800">
                {scanMessage}
              </p>
            ) : null}
          </form>
          {error ? (
            <p className="mt-3 rounded-lg bg-red-50 p-3 text-red-800">
              {error}
            </p>
          ) : null}
          {roster ? (
            <>
              <div className="my-4 grid grid-cols-2 gap-3 md:grid-cols-4">
                <Metric label="Registered" value={roster.registered_total} />
                <Metric label="Onsite now" value={roster.onsite_total} />
                <Metric label="Checked out" value={roster.checked_out_total} />
                <Metric label="Capacity" value={roster.capacity ?? "Open"} />
              </div>
              <div className="max-h-[32rem] space-y-2 overflow-auto">
                {members.map((member) => (
                  <article
                    className="flex flex-wrap items-center justify-between gap-3 rounded-xl border p-3"
                    key={member.membership_id}
                  >
                    <div>
                      <strong>{member.display_name}</strong>
                      <p className="text-sm text-slate-600">
                        {member.email} · {member.membership_type}
                      </p>
                      <p className="text-xs uppercase text-blue-700">
                        {member.entity_code ??
                          member.vendor_code ??
                          member.status.replace("_", " ")}
                      </p>
                      <p className="mt-1 font-mono text-xs text-slate-500">
                        {member.pass_code}
                      </p>
                    </div>
                    {member.status === "checked_in" ? (
                      <button
                        className="rounded-lg border px-4 py-2 font-semibold"
                        disabled={busyId === member.membership_id}
                        onClick={() =>
                          void update(member.membership_id, "checked_out")
                        }
                        type="button"
                      >
                        Check out
                      </button>
                    ) : (
                      <button
                        className="rounded-lg bg-green-700 px-4 py-2 font-semibold text-white disabled:bg-slate-400"
                        disabled={busyId === member.membership_id}
                        onClick={() =>
                          void update(member.membership_id, "checked_in")
                        }
                        type="button"
                      >
                        {member.status === "checked_out"
                          ? "Check in again"
                          : "Check in"}
                      </button>
                    )}
                  </article>
                ))}
                {!members.length ? (
                  <p className="rounded-xl border border-dashed p-5 text-center text-slate-500">
                    No matching event members.
                  </p>
                ) : null}
              </div>
            </>
          ) : null}
        </>
      )}
    </section>
  );
}

function Metric({ label, value }: { label: string; value: number | string }) {
  return (
    <div className="rounded-xl bg-slate-50 p-3">
      <p className="text-xs font-bold uppercase text-slate-500">{label}</p>
      <p className="text-2xl font-bold">{value}</p>
    </div>
  );
}
