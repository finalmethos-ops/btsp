# BTSP Public Cloudflare Tunnel Deployment

## Purchase and account setup

1. Create a Cloudflare account using an organization-controlled email address.
2. Enable phishing-resistant MFA and save the recovery codes offline.
3. In **Domain Registration**, search for the selected standard `.com`.
4. Confirm both the registration and renewal prices before purchasing. Avoid
   premium domains and promotional TLDs with unusually high renewal prices.
5. Enable auto-renew, registrar lock, and DNSSEC.

Cloudflare Registrar keeps the domain on Cloudflare nameservers. This is
expected for this deployment.

For a standalone BTSP identity, prefer a short standard `.com` whose renewal
price is shown before purchase. A name such as `btspplatform.com` is clearer
and more durable than a promotional or free dynamic-DNS subdomain. Registrar
availability is authoritative only at checkout.

## Create the tunnel

In the Cloudflare dashboard:

1. Open **Networking → Tunnels**.
2. Create a remotely managed tunnel named `btsp-production`.
3. Add a published application route for the chosen public hostname.
4. Set the origin service to `https://nginx:4443`. Port `4443` is an
   unpublished Docker-internal listener reserved for the Tunnel connector.
5. Under TLS origin settings, set:
   - **Origin Server Name:** `btsp-origin`
   - **Certificate Authority Pool:**
     `/etc/cloudflared/btsp-intranet-ca.crt`
   - **No TLS Verify:** disabled
6. Leave the final catch-all route configured to return HTTP 404.

For the public hostname:

- Set **SSL/TLS → Edge Certificates → Always Use HTTPS** to enabled.
- Set the minimum TLS version to TLS 1.2.
- Create a Cache Rule that bypasses cache for the entire authenticated
  application hostname. BTSP controls its own static-asset caching.
- Do not enable Rocket Loader or HTML rewriting features.

Copy only the `eyJ...` tunnel token from the generated Docker command. Anyone
with this token can run the tunnel, so treat it as a production secret.

## Store the tunnel token

From the repository root:

```bash
mkdir -p .runtime/cloudflare
```

Save the token as the only line in:

```text
.runtime/cloudflare/tunnel-token
```

On Windows, verify that only the current user, Administrators, and SYSTEM have
access:

```powershell
icacls C:\Users\ultim\Documents\GitHub\btsp\.runtime\cloudflare\tunnel-token
```

Never place the token in Compose, source control, chat, screenshots, or support
tickets. Rotate it in Cloudflare immediately if it is exposed.

## Configure the application hostname

```bash
python3 backend/scripts/configure_public_hostname.py \
  --hostname app.example.com
```

The command adds the public HTTPS origin without removing the private intranet
origin and does not print any environment secrets.

## Start the connector

```bash
docker compose \
  --env-file .env.intranet \
  -p btsp-intranet \
  -f docker-compose.yml \
  -f docker-compose.production.yml \
  -f docker-compose.intranet.yml \
  -f docker-compose.tunnel.yml \
  up -d backend cloudflared
```

The connector publishes no host ports. It maintains outbound connections to
Cloudflare and validates the private certificate presented by Nginx.

`btsp-origin` is a stable certificate identity used only for origin TLS
validation. It is independent of the Windows host's LAN or hotspot address.
The certificate may retain the current LAN address as an additional SAN so
trusted local clients can continue to use the intranet URL.

## Public security checks

- Run `scripts/check-btsp-public-health.sh` from an external monitoring host or
  uptime-monitor worker. It checks the public health and readiness endpoints,
  Cloudflare routing, and the required security headers.
- Run `scripts/check-btsp-production-readiness.sh` before inviting users or
  after a Docker/Windows restart. It combines the public checks with container
  health, duplicate-connector detection, live tunnel metrics, and the nightly
  backup-task result.
- Nginx applies a defense-in-depth limit of 20 login requests per minute per
  client, with a burst of five. FastAPI separately enforces the Redis-backed
  email and client limits plus account lockout.
- The public compose profile binds the optional host fallback listeners to
  loopback only. The origin is therefore reachable through the outbound Tunnel,
  not through a host/LAN port. Keep `BTSP_BIND_ADDRESS=127.0.0.1` unless a
  separately firewalled private-network fallback is intentionally required.
- The Nginx edge rejects common CMS and secret-file probes (`wp-admin`,
  `xmlrpc.php`, `.env`, `.git`, and similar paths) before they reach Next.js.
- Confirm standard login and event login over the public hostname.
- Confirm invalid login throttling and account lockout.
- Confirm vendor, staff, franchise, executive, and administrator role scopes.
- Confirm password-reset email delivery before relying on self-service reset.
- Confirm uploads, downloads, exports, and live event updates.
- Confirm Cloudflare does not cache authenticated HTML or API responses.
- Add a Cloudflare WAF rate-limit rule for authentication endpoints.
- Enable the Cloudflare Managed Ruleset and Bot Fight Mode. Add a custom WAF
  block rule for the same CMS/secret probe paths and a Managed Challenge rule
  for likely automated clients on `/api/v1/auth/login` and password-reset
  endpoints. Rate limiting rules are evaluated before origin delivery and can
  reduce credential stuffing and API abuse.
- Confirm origin audit logs and login throttling distinguish separate client
  IP addresses. Nginx trusts `CF-Connecting-IP` only on the unpublished
  Tunnel listener and overwrites client-supplied forwarding headers.
- Keep the Windows inbound firewall restricted to the private subnet; Tunnel
  requires outbound connectivity only.

## Availability and recovery

- Disable Windows sleep and hibernation while the host is serving production.
- Start Docker Desktop automatically after reboot.
- Keep the `BTSP Production Monitor` scheduled task enabled. In addition to
  reporting health failures, it recreates the stateless Nginx and Cloudflare
  edge containers when a Docker Desktop restart leaves stale WSL bind mounts.
  PostgreSQL, Redis, and application data are not recreated by this repair.
- Keep the computer on a UPS.
- Run `scripts/backup-and-upload-btsp-production.sh` daily to create, restore
  test, and upload encrypted PostgreSQL and durable-file recovery bundles.
- Store the archive passphrase offline and separately from Cloudflare R2.
- Test a restore at least quarterly.
- Monitor the public health endpoint and tunnel status from outside the site.
