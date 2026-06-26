# BTSP Rules

BTSP is built for on-premises first deployment with a cloud-ready design.

## Store Data

The official store data source controls store identity, region, district, and eligibility.

## Access

Users sign in once. Roles control workflow access, routing, store scope, and allowed actions.

## Snapshots

Snapshots are append-only records. Fixes are recorded as new records instead of changing prior records.

## Configuration

Variable business behavior should be configured instead of hard-coded.

## Region Scope

Multi-store ordering must check regional scope before submission.

## Workflow Boundaries

BPP and Independent workflows stay separate across permissions, routing, configuration, reporting, and audit history.
