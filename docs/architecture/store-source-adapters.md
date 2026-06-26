# Store Source Adapters

Store source adapters normalize external store data into the BTSP store batch shape.

## Purpose

Adapters keep source-specific file formats, APIs, schedules, and credentials outside of core store authority logic.

## Contract

A store source adapter must provide:

- `source_system`
- `load()` returning a normalized store batch request

## Current Adapter

The initial adapter is an in-memory adapter used by tests and future administrative tooling.

## Future Adapters

Planned adapters may include:

- CSV file adapter
- Secure upload adapter
- Scheduled API adapter
- Database replication adapter

## Rules

- Store identity remains keyed by store number.
- Region and district values must come from the trusted source feed.
- Ordering eligibility must be explicit.
- Imports should preserve source system and processing metadata.
- Store imports must not merge BPP and Independent workflows.
