# Production Secret Management

BTSP keeps production credentials outside source control in `.env.intranet`
and protected `.runtime` files. The secret audit validates controls without
printing credential values, password fragments, or reusable fingerprints.

## Run the audit

From WSL in the repository:

```bash
python3 scripts/audit-btsp-production-secrets.py
```

The safe JSON report is written to
`.runtime/security/secret-audit.json`. The production-readiness script runs the
same audit automatically. A failed required control exits nonzero; rotation
metadata or Windows ACL review gaps are warnings.

The audit verifies:

- production mode, explicit HTTPS CORS, and loopback-only origin binding;
- non-default minimum length and character diversity for application,
  bootstrap, PostgreSQL, and R2 credentials;
- agreement between `DATABASE_URL` and `POSTGRES_PASSWORD`;
- absence of credential reuse among environment secrets;
- presence of the tunnel token, backup passphrase, TLS private key, and R2
  configuration;
- exclusion of protected files from Git; and
- existence of a rotation ledger with timezone-aware ISO 8601 timestamps; and
- freshness of the secret and Windows ACL reviews, with a 90-day review window.

## Windows ACL review

The repository is mounted into WSL through `v9fs`, which reports synthetic Unix
mode bits. Review the authoritative Windows ACL instead:

```powershell
icacls .env.intranet
icacls .runtime\cloudflare\tunnel-token
icacls .runtime\backup-secrets
icacls .runtime\tls\server\server.key
```

Only the deployment account, Administrators, and SYSTEM should retain access.
Correct inheritance and grants according to organizational policy before
removing the audit warning from an approval record.

## Rotation ledger

Create a private metadata ledger containing dates only:

```powershell
New-Item -ItemType Directory -Force .runtime\security | Out-Null
Copy-Item infrastructure\security\secret-rotation.env.example `
  .runtime\security\secret-rotation.env
notepad .runtime\security\secret-rotation.env
```

Do not put old or current secret values in this file. Rotation itself requires
an approved change window: JWT-key rotation ends active sessions, PostgreSQL
rotation requires synchronized database and application updates, and tunnel or
R2 credential rotation requires provider-side replacement and verification.

If exact dates for already-deployed credentials are unavailable, do not invent
them. Set `CURRENT_SECRET_BASELINE_AT` to the timestamp when the current secret
inventory was verified, retain empty individual `*_ROTATED_AT` fields, and set
`HISTORICAL_ROTATION_DATES_KNOWN=false`. This establishes a conservative age
baseline while explicitly preserving the historical evidence gap. Populate an
individual rotation field only after that credential is actually replaced.
