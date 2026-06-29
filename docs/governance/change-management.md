# BTSP Change and Release Management

## Purpose

This policy defines how application, workflow, configuration, infrastructure, security, and documentation changes move safely into production.

## Required Change Flow

```text
Development
    ↓
Code Review
    ↓
Testing
    ↓
Staging Validation
    ↓
Production Approval
    ↓
Deployment
    ↓
Post-deployment Validation
```

Skipping a stage requires a documented, time-limited emergency exception.

## 1. Development

- Link work to an approved package, change request, defect, policy, or incident.
- State objective, scope, owner, risk, dependencies, data impact, and acceptance criteria.
- Preserve package boundaries and unrelated worktree changes.
- Add or update tests, migrations, seed behavior, documentation, security controls, and observability.
- Never commit production secrets or `.env` files.

## 2. Code Review

Reviewers evaluate:

- Architecture standards and workflow boundaries
- Authentication, authorization, actor trust, and data exposure
- Migration safety, backup timing, and rollback
- Idempotency and concurrency risks
- API compatibility and client impact
- Logging without secret leakage
- Tests for positive, negative, and recovery paths
- Documentation and operational ownership

The author cannot provide the sole production approval for their own high-risk change.

## 3. Testing

- Run format/lint, unit, integration, migration, frontend, and container checks.
- Use supported runtime versions.
- Validate fresh installation and upgrade from the current production revision.
- Validate negative permissions and malformed inputs.
- Validate seeds twice against one database.
- Record exact commands, versions, results, and known failures.

## 4. Staging Validation

- Deploy the immutable candidate artifact with production-mode Compose behavior.
- Use production-like topology and sanitized representative data.
- Exercise health/readiness, authentication, seeds, workflow happy/negative paths, snapshots, notification history, and rollback rehearsal.
- Verify backup and restore before production approval.
- Obtain workflow-owner acceptance for business changes.

## 5. Production Approval

The approval record includes:

- Release ID, Git SHA, and image digests
- Change list and package documentation
- Risk assessment and accepted known issues
- Migration and data-impact notes
- Validation report
- Backup evidence
- Rollback plan and owner
- Architecture, Security, Operations, Platform, and relevant Business approvals
- Deployment window and communications

Missing required evidence produces NO-GO.

## 6. Deployment

- Freeze the approved artifact and configuration.
- Confirm backup completion and restore viability.
- Follow `docs/runbooks/production-deployment.md`.
- Record commands, timestamps, operators, migration revision, and deviations.
- Stop and invoke rollback when acceptance thresholds fail.

## 7. Post-deployment Validation

- Confirm containers, health, readiness, frontend, Nginx, PostgreSQL, and Redis.
- Confirm admin login and authorization boundaries.
- Verify registry, workflow definitions, configuration, snapshots, and notification events.
- Review service logs and metrics.
- Record GO, conditional GO, or rollback decision.
- Close the change only after the observation window completes.

## Change Classes

| Class | Examples | Minimum governance |
|---|---|---|
| Standard | Documentation correction, tested dependency patch | Peer review, CI, release record |
| Normal | Feature, workflow version, schema/config change | Full process and approvals |
| Emergency | Active incident/security mitigation | Incident approval, focused validation, retrospective |

## Configuration-Only Changes

Configuration changes are production changes. Record scope, before/after value, owner, reason, validation, approver, snapshot ID, rollback value, execution time, and post-change evidence. Use least-privilege `configuration.manage` access.

## Dependency Updates

- Review upstream release/security notes and runtime support.
- Keep framework families compatible.
- Regenerate and commit lockfiles.
- Run dependency audit, build, tests, and container validation.
- Prefer supported patched versions over unreviewed forced resolutions.
- Document major upgrades and rollback effects.

## Release Package Requirements

Each release contains:

- Release notes
- Migration notes and current head
- Rollback instructions
- Validation report
- Known issues
- Risk assessment
- Signed/recorded approval record
- Completed platform-readiness and go-live checklist

## Baseline and Tagging

After all approvals and a clean committed candidate, create an annotated immutable tag such as `v1.0.0-platform`. Record the tag, commit SHA, image digests, validation report, and approval record. Never tag a dirty worktree or move an existing release tag.
