# Local Event Demo Accounts

BTSP provides an idempotent, local-only seed for exercising all five event attendee categories. The command refuses to run when `ENVIRONMENT=production`.

```bash
docker compose exec -T backend python -m scripts.seed_event_demo_accounts
```

To create the accounts and a complete, ready-to-use lifecycle event in one step, run:

```bash
docker compose exec -T backend python -m scripts.seed_event_uat
```

This creates the published **BTSP Full Lifecycle UAT** event with Vendor Hall Setup, Live Buying Presentation, Store Loadout and Closeout, and Vendor Buy Fair sub-events. It also adds booth `D-101`, three demo presentation products, and all five demo users as event attendees. The command is idempotent and can be run again safely.

Set `BTSP_DEMO_PASSWORD` or pass `--password` to replace the local default.

The local default password is `BTSP-Demo-2026!`.

| Event category | Account | Event setup qualifier |
| --- | --- | --- |
| Admin | `admin.demo@btsp.local` | None |
| Vendor | `vendor.demo@btsp.local` | Vendor `PERF-001` |
| Franchise representative | `franchise.demo@btsp.local` | Entity `BEBE` |
| Executive | `executive.demo@btsp.local` | None |
| Staff | `staff.demo@btsp.local` | Optional task scope |

The seed activates `PERF-001`, makes its catalog models active and available, ensures three isolated demo models exist, resets the five account passwords, and assigns a single purpose-appropriate role to each identity.

To use the ready-made UAT event:

1. Open `http://localhost:8080/event-login` (recommended) or `http://localhost:3000/event-login`.
2. Sign in with any demo account and the default password (or the password supplied to the seed command).
3. Open My Events and select **BTSP Full Lifecycle UAT**.
4. Use the admin account to configure and operate the event, then use the other identities to validate each attendee-specific experience.

The Event Staff role intentionally omits event administration, system administration, vendor-hall administration, and loadout administration. It permits assigned onsite check-in work only.
