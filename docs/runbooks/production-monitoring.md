# Production Monitoring and Local Log Retention

BTSP uses a lightweight watchdog and bounded Docker log storage for its
single-machine production deployment. No monitoring port or dashboard is
published to the Internet.

## Coverage

Every watchdog run checks:

- public liveness, readiness, Cloudflare routing, and required security headers;
- the state, health, and restart count of each production container;
- host filesystem utilization;
- encrypted production-backup age; and
- recent Nginx 5xx responses.

The production readiness command also reports Cloudflare Tunnel's cumulative
origin-error counter as historical evidence. Because that Prometheus counter
does not reset after recovery, current availability is determined by the live
public health, readiness, homepage, and security-header probes rather than by
requiring the lifetime counter to remain zero.

The watchdog writes JSON Lines records to
`.runtime/monitoring/events.jsonl`. The file rotates at 10 MiB by default and
retains seven local archives. Identical results are still recorded for the
operational ledger, but webhook notifications are emitted only when the result
or status changes. A recovery from `alert` to `healthy` is therefore also
notified.

Docker's `local` logging driver separately retains at most ten compressed
20 MiB log segments per container by default. `docker logs` and
`docker compose logs` continue to work normally.

## Install the watchdog

From PowerShell in the repository:

```powershell
New-Item -ItemType Directory -Force .runtime\monitoring | Out-Null
Copy-Item infrastructure\monitoring\monitor.env.example .runtime\monitoring\monitor.env
notepad .runtime\monitoring\monitor.env
powershell -ExecutionPolicy Bypass -File scripts\register-btsp-monitor-task.ps1
```

Registration creates a hidden `wscript.exe` launcher under
`.runtime\task-launchers`; the five-minute WSL check must not open a console
window. The Windows user must remain signed in for this interactive WSL task.
After registration, manually start the task once and confirm its result is `0`.

The optional `BTSP_ALERT_WEBHOOK_URL` receives a small JSON body containing
only the monitor status and operational findings. Do not place credentials,
user records, or business payloads in monitoring settings or messages.

Run an immediate check from WSL with:

```bash
./scripts/monitor-btsp-production.sh
```

A healthy run exits `0`; an alert exits `1`. Review:

```text
.runtime/monitoring/events.jsonl
.runtime/monitoring/last-check.log
.runtime/monitoring/watchdog.log
```

## Thresholds

| Setting | Default | Purpose |
| --- | ---: | --- |
| `BTSP_MONITOR_DISK_WARNING_PERCENT` | `85` | Alert when the repository filesystem reaches this usage. |
| `BTSP_MONITOR_BACKUP_MAX_AGE_HOURS` | `36` | Alert when no sufficiently recent encrypted backup exists. |
| `BTSP_MONITOR_RESTART_WARNING_COUNT` | `3` | Alert on repeated container restarts. |
| `BTSP_MONITOR_5XX_WARNING_COUNT` | `5` | Alert when recent gateway server errors reach this count. |
| `BTSP_MONITOR_LOG_LOOKBACK` | `6m` | Nginx error-count lookback for a five-minute task interval. |

## Response

Use the matching request ID in the Nginx and backend JSON records when an API
request fails. Follow `operational-alert-escalation.md` for application backlog
alerts and `database-backup-restore.md` for backup failures.

This is bounded, single-host retention. An approved off-host SIEM or managed
log service remains the appropriate later step when regulatory retention,
cross-host search, or a staffed security operations function is required.
