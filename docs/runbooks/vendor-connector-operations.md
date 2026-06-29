# Vendor Connector Operations Runbook

## Required deployment components

- BTSP API and PostgreSQL at migration head.
- A single scheduler trigger, or a distributed scheduler with equivalent mutual exclusion, calling `enqueue-due` at least once per minute.
- One or more supervised connector workers using dedicated identities with only `vendor.connectors.work`.
- An approved external secret provider capable of resolving endpoint `connection_reference` values.
- TLS termination, request logging with authorization-header redaction, and alerts for dead letters and stale leases.

Do not place passwords, tokens, authorization headers, private keys, signed URLs, or URLs containing user information in endpoint configuration.

## Worker sequence

1. Claim one execution with a stable worker ID and a lease long enough for the configured transport timeout.
2. Resolve the opaque connection reference outside BTSP.
3. Fetch the remote object without logging credentials or response bodies.
4. Submit normalized content through the endpoint import API.
5. Report success with the completed import-run ID, or report a bounded error message.
6. Discard the lease token. It is returned once and cannot be recovered from the database.

Never retry transport work outside the recorded BTSP execution lifecycle. Doing so hides attempts and can duplicate remote operations.

## Dead letters

Investigate the recorded error, endpoint status, partner availability, and import history before replay. Correct configuration first. Replay only through the operations UI or replay API so the decision is audited.

## Security validation

Run inside the backend deployment:

```sh
python -m scripts.validate_001t_security
```

The check fails if endpoint configuration contains likely credential material, an active lease is malformed or expired, or the system-admin role lacks required 001T permissions. It reports counts only and never outputs endpoint configuration, lease digests, or credentials.

## Incident response

If a worker identity or lease token is suspected compromised:

1. Disable the worker identity and rotate its authentication credential.
2. Stop the affected worker deployment.
3. Allow active leases to expire; do not edit lease digests directly.
4. Run the security validation and inspect execution audit snapshots.
5. Rotate vendor credentials in the external secret provider when exposure cannot be excluded.
6. Resume workers and replay verified dead letters.
