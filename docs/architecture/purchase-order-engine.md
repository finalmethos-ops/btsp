# Purchase Order Engine

## Boundary

The Purchase Order Engine converts eligible Purchase Requests into durable purchasing artifacts.
The workflow remains responsible for approval and lifecycle state; PO generation is allowed only
when the source request reaches `po_created`.

No external vendor API, EDI, or client integration is part of the initial 001S baseline. Future
transmission records describe internal export and operator-controlled delivery activity.

## Identity and numbering

PO numbers use a configurable prefix, calendar year, and zero-padded annual sequence. PostgreSQL
generation uses a transaction-scoped advisory lock plus a persisted sequence row, preventing two
concurrent transactions from issuing the same number. The default format is:

```text
PO-YYYY-000001
```

Configuration is stored under `purchase_order / default / numbering`:

```json
{"prefix": "PO", "padding": 6}
```

## Source preservation

Each PO records its source Purchase Requests and each PO line records its source request line. Product
description, quantity, unit price, freight, tax, and extended amount are copied into the PO line.
Later catalog or request changes therefore cannot rewrite an issued purchasing artifact.

Requests are grouped only when workflow, vendor, and currency match; BPP and Independent purchasing
can never be consolidated together. When configured limits split a request, its source link may
appear on each generated PO, while every copied PO line retains its unique source-line identity.
Subsequent generation from that request remains prohibited.

## Internal transmission

Transmission is an audited state machine over an immutable artifact. The initial implementation
records operator-controlled handoff only and has no external side effect. Immutable transmission
events and platform snapshots distinguish prepared, released, delivered, failed, retried, and
cancelled activity without pretending that a third party acknowledged delivery.
