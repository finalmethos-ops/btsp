# ADR 0001: On-Premises First, Cloud-Ready Architecture

## Status

Accepted

## Context

BTSP must support an on-premises deployment model first, while avoiding design choices that would prevent later cloud deployment.

## Decision

The application will use containerized services, environment-based configuration, PostgreSQL, Redis, FastAPI, Next.js, and Nginx.

## Consequences

- Local and on-premises deployments can use Docker Compose.
- Later cloud deployment can reuse the same service boundaries.
- Configuration must be externalized through environment variables and database-backed configuration tables.
