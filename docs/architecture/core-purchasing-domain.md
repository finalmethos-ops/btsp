# Core Purchasing Domain

## Boundary

BTSP owns an internal PostgreSQL catalog populated from controlled Excel workbooks. It does not
connect to vendor clients, vendor APIs, EDI services, or external product databases in 001R.

The catalog is current reference data. A purchase request is transactional data. A line item keeps
the catalog product code and name but snapshots the unit price used when the line was created or
edited. Later catalog imports therefore do not rewrite existing request economics.

## Aggregate

`PurchaseRequest` is the aggregate root. It owns its line items, store and vendor references,
workflow reference, status, totals, context, and audit identity. Draft changes recalculate:

`total = subtotal + freight_total + tax_total`

The Official Store Database table remains authoritative for store activation, ordering eligibility,
and region scope. Catalog products remain authoritative for vendor association, availability,
minimum quantity, and current price.

The workflow instance remains the authoritative lifecycle record. A small domain projection hook
updates `purchase_requests.status` after each workflow transition so purchasing queries expose the
current state without duplicating transition logic.

## Excel contract

The canonical `.xlsx` workbook contains two sheets:

- `Vendors`: required `vendor_code`, `name`; optional `is_active`.
- `Products`: required `product_code`, `vendor_code`, `name`, `unit_price`; optional
  `model_number`, `category`, `brand`, `currency`, `minimum_order_quantity`, `is_available`, and
  `is_active`.

Imports are validated before writes and upsert by stable vendor/product code. Re-importing a file
does not create duplicate catalog records. Products may only reference vendors included in the same
workbook. Boolean cells accept true/false, yes/no, y/n, and 1/0.

Catalog rows should be deactivated through a subsequent workbook rather than deleted, preserving
historical references.
