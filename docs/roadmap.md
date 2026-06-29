# BTSP Product Roadmap

BTSP evolves from reusable platform services into purchasing domain capabilities and then into
operational integrations, reconciliation, reporting, and administration.

## Epic sequence

| Epic | Name | Outcome |
| --- | --- | --- |
| 001A–001O | Platform Foundation | Repository, identity, configuration, workflow, and frontend foundations |
| 001P | BPP Workflow Platform | BPP workflow definitions, policies, and notifications |
| 001Q | Independent Workflow Platform | Independent purchasing workflow and regional controls |
| 001R | Core Purchasing Domain Model | Purchase Requests, catalog lines, rules, drafts, attachments, validation, and APIs |
| 001S | Purchase Order Engine | PO numbering, vendor grouping, splitting, consolidation, artifacts, exports, and internal transmission lifecycle |
| 001T | Vendor Integration Platform | Vendor acknowledgements, shipment updates, ASN, EDI/API integrations, and import automation |
| 001U | Receiving and Reconciliation | Receiving, variances, backorders, invoice matching, reconciliation, and exception workflows |
| 001V | Inventory and Analytics | Dashboards, KPIs, spend analysis, vendor scorecards, approval analytics, and workflow metrics |
| 001W | Administration Platform | User and role management, configuration, workflow and notification administration, system health, and audit reporting |

Completion of 001W establishes the BTSP v1.0 capability baseline.

Package 001W.6 consolidates administration security and the final production-validation gate for
that baseline. A capability-complete development candidate is not a production-approved release
until the immutable-candidate and human-approval requirements are satisfied.

## Architecture boundary

Epics 001O–001Q establish platform services: the workflow engine, workflow definitions, policies,
and notifications. Epic 001R establishes the business entities those services operate on. Epic
001S and later epics add operational capabilities around that domain model.

This separation allows future workflows—such as returns, transfers, and inventory adjustments—to
reuse the platform without redesigning the purchasing model.

The 001S transmission lifecycle records internal preparation and operator-controlled handoff. It
does not imply that a vendor received or accepted a purchase order. Vendor-facing delivery,
acknowledgement, ASN, EDI, API, and automated import behavior belongs to 001T.

## Delivery progression

```text
001A–001O  Platform Foundation
    |
001P       BPP Workflow Platform
    |
001Q       Independent Workflow Platform
    |
001R       Core Purchasing Domain Model
    |
001S       Purchase Order Engine
    |
001T       Vendor Integration Platform
    |
001U       Receiving and Reconciliation
    |
001V       Inventory and Analytics
    |
001W       Administration Platform
    |
BTSP v1.0
```
