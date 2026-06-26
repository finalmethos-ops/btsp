# Snapshots

Snapshots are append-only audit records for important BTSP actions.

## Purpose

Snapshots preserve what happened, who initiated it, when it happened, and the relevant payload known at that time.

## Rules

- Snapshot rows are append-only.
- Prior rows are not edited to correct history.
- Corrections are represented as new rows.
- Each row should include actor, type, subject type, subject id, and payload.
- Payloads should be concise and relevant.

## Current Sources

- Store batch processing writes a summary row.

## Future Sources

- Login activity
- Order creation
- Order approval
- Order submission
- Store feed runs
- Workflow setting changes
- Region scope exceptions
