# 0048 — Model Number Identifiers

## Outcome

Model number is now the canonical business identifier and visible label for catalog models. Internal synthetic codes such as `PERF-0001` are no longer shown or accepted as the identity of a populated model.

## Behavior

- Existing populated model identifiers are migrated to their normalized model numbers.
- Purchase requests, purchase orders, receipts, backorders, ASNs, invoices, and cost history retain consistent references.
- Catalog responses expose `model_identifier`, equal to the model number.
- Vendor and administrative model screens display model number as the primary label.
- New catalog and vendor-model imports require `model_number` and derive the internal product key from it.
- Model numbers are unique. The owning vendor may rename one; the canonical key and
  all purchasing, receiving, invoice, shipment, and cost-history references follow
  the replacement atomically.
- Legacy catalog rows without a model number remain available for historical referential integrity but are excluded from selectable model catalogs.

## Persistence

Migration `0048_model_identifiers` adds model-number uniqueness, enables cascading catalog identifier updates, and replaces populated synthetic identifiers transactionally.
