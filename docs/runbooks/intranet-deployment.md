# BTSP Private-Network Deployment

## Scope

This runbook deploys BTSP from one Windows/Docker Desktop host for users on the
same trusted private network. It does not expose PostgreSQL, Redis, the backend,
or the frontend directly. Nginx is the only published service.

The development stack remains on port `8080`. The hardened intranet stack uses
port `18080` until an explicit cutover.

## Stable host address

Reserve the Windows host address in the router or assign a static private
address before distributing the URL. A DHCP address change will otherwise
invalidate bookmarks and the configured browser origin.

## Generate private configuration

From the repository root:

```bash
python3 backend/scripts/generate_intranet_env.py \
  --host 192.168.0.146 \
  --port 18080
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
curl -f http://192.168.0.146:18080/api/v1/health
curl -f http://192.168.0.146:18080/api/v1/ready
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

- Allow the chosen port only from the trusted private subnet.
- Do not configure router port forwarding, UPnP exposure, or a public tunnel.
- Keep PostgreSQL, Redis, backend, and frontend ports unpublished.
- HTTP does not encrypt credentials. Use only on a trusted isolated LAN, or add
  an internally trusted TLS certificate before real credentials are used.
- Enable the Windows Firewall and create a subnet-scoped inbound rule before
  production cutover.

For the current `192.168.0.0/24` network, run these commands from an elevated
PowerShell prompt after confirming the adapter name:

```powershell
Set-NetConnectionProfile -InterfaceAlias "Ethernet 2" -NetworkCategory Private
Set-NetFirewallProfile -Profile Domain,Private,Public -Enabled True
New-NetFirewallRule -DisplayName "BTSP Intranet 18080" `
  -Direction Inbound -Action Allow -Protocol TCP -LocalPort 18080 `
  -RemoteAddress 192.168.0.0/24 -Profile Private
```

Review existing inbound services before enabling the firewall so remote access
or file-sharing rules are not unintentionally interrupted.

## External service dependency

The BTSP UI and core data stay on the intranet. Route calculation currently
uses the configured geocoding and routing services, so that feature requires
outbound internet access unless equivalent internal services are configured.

## Cutover

When acceptance is complete, schedule a short write freeze, make a final
database and durable-volume copy, stop the development stack, and move the
intranet Nginx port to `8080` (or `80`). Do not run both projects on the same
host port.
