# BTSP Private-Network Deployment

## Scope

This runbook deploys BTSP from one Windows/Docker Desktop host for users on the
same trusted private network. It does not expose PostgreSQL, Redis, the backend,
or the frontend directly. Nginx is the only published service.

The development stack remains on port `8080`. The parallel intranet stack uses
HTTPS on port `18443`; port `18080` exists only to redirect clients to HTTPS.

## Stable host address

Reserve the Windows host address in the router or assign a static private
address before distributing the URL. A DHCP address change will otherwise
invalidate bookmarks and the configured browser origin.

## Generate private configuration

From the repository root:

```bash
python3 backend/scripts/generate_intranet_env.py \
  --host 192.168.0.146 \
  --port 18080 \
  --tls-port 18443
```

The command creates `.env.intranet` with unique database, JWT, and bootstrap
secrets. It refuses to overwrite an existing file. On Linux it requests mode
`0600`; on a Windows-mounted repository, Windows ACLs are authoritative. Confirm
that only the current user, Administrators, and SYSTEM can read the file:

```powershell
icacls C:\Users\ultim\Documents\GitHub\btsp\.env.intranet
```

Validate the merged configuration without printing secrets:

```bash
docker compose \
  --env-file .env.intranet \
  -p btsp-intranet \
  -f docker-compose.yml \
  -f docker-compose.production.yml \
  -f docker-compose.intranet.yml \
  config --quiet
```

## Initial data copy

Create and verify a current backup before copying data. Start only the isolated
database and Redis services, then stream the current database into the new
project:

```bash
docker compose \
  --env-file .env.intranet \
  -p btsp-intranet \
  -f docker-compose.yml \
  -f docker-compose.production.yml \
  -f docker-compose.intranet.yml \
  up -d postgres redis

docker compose exec -T postgres \
  pg_dump -U btsp -d btsp -Fc --no-owner --no-acl |
docker compose \
  --env-file .env.intranet \
  -p btsp-intranet \
  -f docker-compose.yml \
  -f docker-compose.production.yml \
  -f docker-compose.intranet.yml \
  exec -T postgres \
  pg_restore -U btsp -d btsp --no-owner --no-acl
```

Copy each durable file volume read-only from the development project into its
corresponding empty `btsp-intranet_*` volume. Never copy a live PostgreSQL data
directory; use `pg_dump`/`pg_restore` as shown above.

The durable file volumes are:

- `attachment_data`
- `purchase_order_export_data`
- `analytics_report_data`
- `invoice_intake_data`

## Start and validate

```bash
docker compose \
  --env-file .env.intranet \
  -p btsp-intranet \
  -f docker-compose.yml \
  -f docker-compose.production.yml \
  -f docker-compose.intranet.yml \
  up -d

docker compose \
  --env-file .env.intranet \
  -p btsp-intranet \
  -f docker-compose.yml \
  -f docker-compose.production.yml \
  -f docker-compose.intranet.yml \
  exec backend alembic upgrade head
```

Validate from the host and a second private-network device:

```bash
curl --cacert .runtime/tls/authority/btsp-intranet-ca.crt \
  -f https://192.168.0.146:18443/api/v1/health
curl --cacert .runtime/tls/authority/btsp-intranet-ca.crt \
  -f https://192.168.0.146:18443/api/v1/ready
```

Then confirm event login, standard login, role scoping, file upload/download,
and a container restart.

## Backups

Keep the PostgreSQL custom-format dump and archives of all four durable file
volumes together. Verify a database dump before relying on it:

```bash
docker run --rm \
  -v "/mnt/c/Users/ultim/Documents/BTSP Backups:/backup:ro" \
  postgres:16-alpine \
  pg_restore --list /backup/<backup-name>.dump
```

Store a second copy off this computer. A backup on the application host protects
against bad changes, but not host loss or disk failure.

## Network security

- Allow the redirect and HTTPS ports only from the trusted private subnet.
- Do not configure router port forwarding, UPnP exposure, or a public tunnel.
- Keep PostgreSQL, Redis, backend, and frontend ports unpublished.
- Never bypass the HTTPS endpoint when entering credentials.
- Enable the Windows Firewall and create a subnet-scoped inbound rule before
  production cutover.

For the current `192.168.0.0/24` network, run the repository's idempotent setup
script from an elevated PowerShell prompt:

```powershell
.\scripts\configure-btsp-intranet-firewall.ps1 `
  -InterfaceAlias "Ethernet 2" `
  -Ports 18080,18443 `
  -RemoteSubnet "192.168.0.0/24"
```

Review existing inbound services before enabling the firewall so remote access
or file-sharing rules are not unintentionally interrupted.

## Internal HTTPS

Generate the private certificate authority and server certificate:

```bash
./scripts/generate-btsp-intranet-certificates.sh \
  192.168.0.146 \
  .runtime/tls \
  btsp-origin
```

Install `.runtime/tls/authority/btsp-intranet-ca.crt` in the trusted-root store
on Windows and on each authorized phone or workstation. The CA private key must
never be installed on client devices. Keep it access-restricted and include it
only in the protected configuration backup.

The intranet profile exposes HTTPS on `18443`. HTTP on `18080` performs a
permanent redirect and does not serve the application.

For iOS/iPadOS, transfer only `btsp-intranet-ca.crt`, install the downloaded
profile, then enable full trust under **Settings → General → About →
Certificate Trust Settings**. For Android, install the same public certificate
as a **CA certificate** under the device's security credential settings. Device
management policies may require an administrator to perform these steps.

After trust is installed, open:

```text
https://192.168.0.146:18443
```

Never transfer `btsp-intranet-ca.key` or `server.key` to a client device.

## External service dependency

The BTSP UI and core data stay on the intranet. Route calculation currently
uses the configured geocoding and routing services, so that feature requires
outbound internet access unless equivalent internal services are configured.

## Cutover

When acceptance is complete, schedule a short write freeze, make a final
database and durable-volume copy, then make the intranet project the sole
writable environment. Keep the development project stopped during real use so
the two databases cannot diverge. Moving to standard ports `80` and `443`
requires updating both the Compose port mapping and the HTTP redirect target.
