# Operational Alert Escalation

The System Health view classifies operational backlogs as `info`, `warning`, or
`critical`. A non-zero warning or critical metric marks the overall health state
as degraded; unavailable dependencies or storage are reported as unavailable.

## Threshold configuration

These environment variables can be tuned per deployment:

| Variable | Default | Meaning |
| --- | ---: | --- |
| `CRITICAL_NOTIFICATION_THRESHOLD` | `100` | Failed or queued notifications at or above this count are critical. |
| `CRITICAL_OPERATIONAL_THRESHOLD` | `10` | Other operational backlogs at or above this count are critical. |
| `STALE_NOTIFICATION_AFTER_MINUTES` | `15` | Queued notifications older than this age are tracked as stale; any stale item is critical. |

Values are validated as positive integers at application startup. Changes take
effect after the backend process reloads.

## Response procedure

1. Open Administration → System Health and identify the critical metric.
2. For notification backlog, review Administration → Notifications and retry
   failed events after correcting the underlying delivery issue.
3. For event task backlog, open the affected event and assign or complete
   blocked/overdue tasks.
4. Verify the metric returns to `info` and the overall health state returns to
   `healthy`.

The health endpoint is read-only and does not automatically retry notifications
or change task state.
