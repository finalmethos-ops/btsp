# BTSP Platform Baseline v1.0 Approval Record

## Candidate

- Milestone: BTSP Platform Baseline v1.0
- Proposed tag: `v1.0.0-platform`
- Candidate commit SHA: Pending clean commit
- Backend image digest: Pending final committed build
- Frontend image digest: Pending final committed build
- Validation report: `docs/validation/001P-production-validation.md`
- Release notes: `docs/releases/001P-release-notes.md`
- Known issues: `docs/releases/001P-known-issues.md`
- Rollback plan: `docs/releases/001P-rollback-plan.md`
- Deployment checklist: `docs/releases/001P-deployment-checklist.md`

## Technical Readiness

- Governance artifact completeness: Pass
- Production Compose build/start: Pass
- PostgreSQL migration: Pass, `0008_notification_framework`
- Backend tests/Ruff: Pass, 68 tests
- Frontend build/tests: Pass, 5 tests
- Health/readiness: Pass
- 001P live production validation: Pass
- Worktree clean and committed: Pending

## Risk Assessment

Accepted limitations and required operational treatments are listed in `001P-known-issues.md`. Highest current governance gaps are centralized metrics/log correlation and dedicated audit producers for login, permission changes, and unified administrative actions. These gaps require ownership and roadmap decisions but do not invalidate the tested workflow platform behavior.

## Required Approvals

| Approval | Approver | Decision | Timestamp | Conditions/record |
|---|---|---|---|---|
| Architecture Owner | Pending | Pending | Pending | Confirm architecture freeze and exception register |
| Security Owner | Pending | Pending | Pending | Confirm security checklist and audit-gap treatment |
| Platform Owner | Pending | Pending | Pending | Accept scope, known issues, and roadmap |
| Operations/Recovery Owner | Pending | Pending | Pending | Accept monitoring, backup, restore, and DR duties |
| BPP Workflow/Business Owner | Pending | Pending | Pending | Accept workflow behavior and lifecycle ownership |
| Release Manager | Pending | Pending | Pending | Confirm immutable SHA/images and evidence package |

## Tag Authorization

Do not create or publish `v1.0.0-platform` until:

1. The complete candidate is committed and the worktree is clean.
2. Final image digests are recorded.
3. Every required approval above is completed.
4. Conditions and time-limited exceptions have owners and due dates.
5. The Release Manager authorizes the annotated tag.

After authorization, create an annotated tag without moving or reusing an existing release tag, and record the published tag and artifact digests here.
