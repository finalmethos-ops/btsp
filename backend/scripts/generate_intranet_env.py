from __future__ import annotations

import argparse
import ipaddress
import os
import secrets
from pathlib import Path

PRIVATE_NETWORKS = tuple(
    ipaddress.IPv4Network(network)
    for network in ("10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16")
)


def private_ipv4(value: str) -> str:
    try:
        address = ipaddress.IPv4Address(value)
    except ipaddress.AddressValueError as exc:
        raise argparse.ArgumentTypeError("host must be a valid IPv4 address") from exc
    if not any(address in network for network in PRIVATE_NETWORKS):
        raise argparse.ArgumentTypeError("host must be an RFC 1918 private IPv4 address")
    return str(address)


def tcp_port(value: str) -> int:
    port = int(value)
    if port < 1 or port > 65535:
        raise argparse.ArgumentTypeError("port must be between 1 and 65535")
    return port


def render_environment(host: str, port: int, tls_port: int = 18443) -> str:
    database_password = secrets.token_hex(32)
    return f"""# Generated BTSP intranet production environment.
# Keep this file private. It is excluded by .gitignore.
COMPOSE_PROJECT_NAME=btsp-intranet
ENVIRONMENT=production
APP_NAME=BTSP
APP_VERSION=1.0.0-rc.3

NEXT_PUBLIC_API_BASE_URL=
NEXT_ALLOWED_DEV_ORIGINS=

API_HOST=0.0.0.0
API_PORT=8000
SECRET_KEY={secrets.token_hex(48)}
BOOTSTRAP_ADMIN_TOKEN={secrets.token_hex(32)}
ACCESS_TOKEN_EXPIRE_MINUTES=60
REFRESH_TOKEN_EXPIRE_DAYS=14
PASSWORD_RESET_EXPIRE_MINUTES=30
LOGIN_LOCKOUT_THRESHOLD=5
LOGIN_LOCKOUT_MINUTES=15
LOGIN_RATE_LIMIT_WINDOW_SECONDS=300
LOGIN_RATE_LIMIT_EMAIL_ATTEMPTS=8
LOGIN_RATE_LIMIT_HOST_ATTEMPTS=40
CORS_ORIGINS=https://{host}:{tls_port}
BRAVE_SEARCH_API_KEY=
GEOCODING_API_URL=https://nominatim.openstreetmap.org/search
ROUTING_API_URL=https://router.project-osrm.org/route/v1/driving
NOTIFICATION_EMAIL_ENABLED=false
NOTIFICATION_WEBHOOK_ENABLED=false
SMTP_HOST=
SMTP_PORT=587
SMTP_USERNAME=
SMTP_PASSWORD=
SMTP_FROM=no-reply@btsp.local
NOTIFICATION_DELIVERY_TIMEOUT_SECONDS=10
EVENT_TASK_REMINDER_INTERVAL_SECONDS=300
ATTACHMENT_STORAGE_PATH=/data/attachments
ATTACHMENT_MAX_BYTES=20971520
PURCHASE_ORDER_EXPORT_PATH=/data/purchase-order-exports
ANALYTICS_REPORT_PATH=/data/analytics-reports
INVOICE_INTAKE_STORAGE_PATH=/data/invoice-intake

POSTGRES_DB=btsp
POSTGRES_USER=btsp
POSTGRES_PASSWORD={database_password}
DATABASE_URL=postgresql+psycopg://btsp:{database_password}@postgres:5432/btsp
REDIS_URL=redis://redis:6379/0

BTSP_BIND_ADDRESS=0.0.0.0
NGINX_PORT={port}
NGINX_TLS_PORT={tls_port}
"""


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Create an ignored BTSP intranet environment file with unique secrets."
    )
    parser.add_argument("--host", required=True, type=private_ipv4)
    parser.add_argument("--port", default=18080, type=tcp_port)
    parser.add_argument("--tls-port", default=18443, type=tcp_port)
    parser.add_argument("--output", default=".env.intranet", type=Path)
    args = parser.parse_args()

    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    descriptor = os.open(args.output, flags, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(render_environment(args.host, args.port, args.tls_port))
    print(f"Created {args.output} for https://{args.host}:{args.tls_port}")


if __name__ == "__main__":
    main()
