#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
from datetime import UTC, datetime, timedelta
from pathlib import Path
from urllib.parse import unquote, urlsplit


KNOWN_DEFAULTS = {
    "btsp_local_password",
    "change-me-before-bootstrap",
    "change-me-before-production",
}


def parse_utc_timestamp(value: str) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return None
    return parsed.astimezone(UTC)


def read_environment(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for line_number, raw_line in enumerate(
        path.read_text(encoding="utf-8").splitlines(), start=1
    ):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].strip()
        if "=" not in line:
            raise ValueError(f"Invalid environment entry at {path}:{line_number}")
        key, value = line.split("=", 1)
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
            value = value[1:-1]
        values[key.strip()] = value
    return values


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Audit BTSP production secret controls without displaying secret values."
    )
    parser.add_argument("--env-file", default=".env.intranet")
    parser.add_argument("--r2-env-file", default=".runtime/backup-secrets/r2.env")
    parser.add_argument("--runtime-directory", default=".runtime")
    parser.add_argument("--output", default=".runtime/security/secret-audit.json")
    args = parser.parse_args()

    root = Path.cwd()
    env_path = root / args.env_file
    r2_path = root / args.r2_env_file
    runtime = root / args.runtime_directory
    output_path = root / args.output
    checks: list[dict[str, str]] = []

    def add(code: str, status: str, message: str) -> None:
        checks.append({"code": code, "status": status, "message": message})

    if not env_path.is_file():
        add("environment.file", "fail", "Production environment file is missing.")
        environment: dict[str, str] = {}
    else:
        environment = read_environment(env_path)
        add("environment.file", "pass", "Production environment file is present.")

    if not r2_path.is_file():
        add("r2.file", "fail", "Private R2 environment file is missing.")
        r2_environment: dict[str, str] = {}
    else:
        r2_environment = read_environment(r2_path)
        add("r2.file", "pass", "Private R2 environment file is present.")

    secret_values: dict[str, str] = {}

    def check_secret(
        source: dict[str, str],
        key: str,
        minimum_bytes: int,
        *,
        label: str | None = None,
    ) -> None:
        display_name = label or key
        value = source.get(key, "")
        if not value:
            add(f"secret.{key.lower()}", "fail", f"{display_name} is missing or empty.")
            return
        secret_values[key] = value
        if value.casefold() in KNOWN_DEFAULTS or "change-me" in value.casefold():
            add(
                f"secret.{key.lower()}", "fail", f"{display_name} uses a known default."
            )
            return
        if len(value.encode("utf-8")) < minimum_bytes:
            add(
                f"secret.{key.lower()}",
                "fail",
                f"{display_name} is shorter than the {minimum_bytes}-byte minimum.",
            )
            return
        if len(set(value)) < 12:
            add(
                f"secret.{key.lower()}",
                "fail",
                f"{display_name} does not have sufficient character diversity.",
            )
            return
        add(
            f"secret.{key.lower()}",
            "pass",
            f"{display_name} passes non-default length and diversity checks.",
        )

    check_secret(environment, "SECRET_KEY", 48)
    check_secret(environment, "BOOTSTRAP_ADMIN_TOKEN", 32)
    check_secret(environment, "POSTGRES_PASSWORD", 24)
    check_secret(
        r2_environment, "RCLONE_CONFIG_R2_ACCESS_KEY_ID", 16, label="R2 access key"
    )
    check_secret(
        r2_environment,
        "RCLONE_CONFIG_R2_SECRET_ACCESS_KEY",
        32,
        label="R2 secret access key",
    )

    archive_passphrase_path = runtime / "backup-secrets/archive-passphrase"
    tunnel_token_path = runtime / "cloudflare/tunnel-token"
    tls_private_key_path = runtime / "tls/server/server.key"
    protected_paths = [
        env_path,
        r2_path,
        archive_passphrase_path,
        tunnel_token_path,
        tls_private_key_path,
    ]

    def check_secret_file(path: Path, code: str, minimum_bytes: int) -> None:
        if not path.is_file() or path.stat().st_size < minimum_bytes:
            add(
                code,
                "fail",
                f"Protected file {path} is missing, empty, or unexpectedly short.",
            )
        else:
            add(code, "pass", f"Protected file {path} is present and non-empty.")

    check_secret_file(archive_passphrase_path, "secret.backup_passphrase", 32)
    check_secret_file(tunnel_token_path, "secret.cloudflare_tunnel_token", 80)
    check_secret_file(tls_private_key_path, "secret.tls_private_key", 100)

    present_values = [(name, value) for name, value in secret_values.items() if value]
    reused_pairs = [
        f"{left_name}/{right_name}"
        for index, (left_name, left_value) in enumerate(present_values)
        for right_name, right_value in present_values[index + 1 :]
        if left_value == right_value
    ]
    if reused_pairs:
        add(
            "secret.reuse",
            "fail",
            "Secret reuse was detected between: " + ", ".join(reused_pairs),
        )
    else:
        add(
            "secret.reuse",
            "pass",
            "No reuse was detected among environment credentials.",
        )

    database_url = environment.get("DATABASE_URL", "")
    try:
        database_password = unquote(urlsplit(database_url).password or "")
    except ValueError:
        database_password = ""
    if not database_password:
        add(
            "database.url",
            "fail",
            "DATABASE_URL does not contain a parseable password.",
        )
    elif database_password != environment.get("POSTGRES_PASSWORD"):
        add("database.url", "fail", "DATABASE_URL and POSTGRES_PASSWORD do not agree.")
    else:
        add("database.url", "pass", "Database credentials are internally consistent.")

    if environment.get("ENVIRONMENT", "").casefold() != "production":
        add("environment.mode", "fail", "ENVIRONMENT is not production.")
    else:
        add("environment.mode", "pass", "Production mode is explicitly enabled.")

    if environment.get("BOOTSTRAP_ENABLED", "").casefold() not in {"false", "0", "no", "off"}:
        add(
            "bootstrap.disabled",
            "fail",
            "Administrative bootstrap is not explicitly disabled in production.",
        )
    else:
        add(
            "bootstrap.disabled",
            "pass",
            "Administrative bootstrap is explicitly disabled in production.",
        )

    origins = [
        value.strip()
        for value in environment.get("CORS_ORIGINS", "").split(",")
        if value.strip()
    ]
    if not origins or any(not origin.startswith("https://") for origin in origins):
        add(
            "network.cors",
            "fail",
            "CORS contains an empty or non-HTTPS production origin.",
        )
    elif any("localhost" in origin or "*" in origin for origin in origins):
        add(
            "network.cors",
            "fail",
            "CORS contains a local or wildcard production origin.",
        )
    else:
        add("network.cors", "pass", "CORS is restricted to explicit HTTPS origins.")

    if environment.get("BTSP_BIND_ADDRESS") != "127.0.0.1":
        add(
            "network.origin_bind",
            "fail",
            "The fallback origin listener is not loopback-only.",
        )
    else:
        add(
            "network.origin_bind",
            "pass",
            "The fallback origin listener is loopback-only.",
        )

    tracked_paths: list[str] = []
    for protected_path in protected_paths:
        relative_path = str(protected_path.relative_to(root))
        tracked = subprocess.run(
            ["git", "ls-files", "--error-unmatch", relative_path],
            cwd=root,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        if tracked.returncode == 0:
            tracked_paths.append(relative_path)
    if tracked_paths:
        add(
            "source_control.protected_files",
            "fail",
            "Protected runtime files are tracked by Git: " + ", ".join(tracked_paths),
        )
    else:
        add(
            "source_control.protected_files",
            "pass",
            "Production environment, key, token, and backup-secret files are not tracked by Git.",
        )

    rotation_record = runtime / "security/secret-rotation.env"
    rotation_keys = [
        "SECRET_KEY_ROTATED_AT",
        "BOOTSTRAP_ADMIN_TOKEN_ROTATED_AT",
        "POSTGRES_PASSWORD_ROTATED_AT",
        "CLOUDFLARE_TUNNEL_TOKEN_ROTATED_AT",
        "R2_ACCESS_KEY_ROTATED_AT",
        "BACKUP_PASSPHRASE_ROTATED_AT",
        "TLS_PRIVATE_KEY_ROTATED_AT",
    ]
    if not rotation_record.is_file():
        add(
            "rotation.record",
            "warning",
            "Secret rotation dates are not yet recorded in the private rotation ledger.",
        )
        add(
            "filesystem.windows_acl",
            "warning",
            "This WSL v9fs mount does not expose authoritative Windows ACLs; verify protected paths with icacls.",
        )
    else:
        rotation_values = read_environment(rotation_record)
        now = datetime.now(UTC)
        reviewed_at = parse_utc_timestamp(rotation_values.get("REVIEWED_AT", ""))
        if reviewed_at is None:
            add(
                "rotation.review",
                "warning",
                "The rotation ledger review date is missing or is not a timezone-aware ISO 8601 timestamp.",
            )
        elif reviewed_at > now + timedelta(minutes=5):
            add(
                "rotation.review",
                "warning",
                "The rotation ledger review date is unexpectedly in the future.",
            )
        elif reviewed_at < now - timedelta(days=90):
            add(
                "rotation.review",
                "warning",
                "The private rotation ledger review is more than 90 days old.",
            )
        else:
            add(
                "rotation.review",
                "pass",
                "The private rotation ledger has a current, valid review timestamp.",
            )
        missing_rotation_dates = [
            key for key in rotation_keys if not rotation_values.get(key, "")
        ]
        invalid_rotation_dates = [
            key
            for key in rotation_keys
            if rotation_values.get(key, "")
            and parse_utc_timestamp(rotation_values[key]) is None
        ]
        baseline_at = parse_utc_timestamp(
            rotation_values.get("CURRENT_SECRET_BASELINE_AT", "")
        )
        historical_dates_known = rotation_values.get(
            "HISTORICAL_ROTATION_DATES_KNOWN", ""
        ).casefold()
        managed_unknown_history = (
            baseline_at is not None
            and baseline_at <= now + timedelta(minutes=5)
            and historical_dates_known == "false"
        )
        if missing_rotation_dates and managed_unknown_history:
            add(
                "rotation.record",
                "pass",
                "Current credentials have a managed age baseline; pre-baseline rotation history is explicitly recorded as unknown.",
            )
        elif missing_rotation_dates:
            add(
                "rotation.record",
                "warning",
                "Rotation dates remain undocumented for: "
                + ", ".join(missing_rotation_dates),
            )
        else:
            add(
                "rotation.record",
                "pass",
                "All required secret rotation dates are recorded.",
            )
        if (
            rotation_values.get("CURRENT_SECRET_BASELINE_AT", "")
            and baseline_at is None
        ):
            add(
                "rotation.baseline",
                "warning",
                "The current-secret baseline is not a timezone-aware ISO 8601 timestamp.",
            )
        elif baseline_at is not None and baseline_at > now + timedelta(minutes=5):
            add(
                "rotation.baseline",
                "warning",
                "The current-secret baseline is unexpectedly in the future.",
            )
        if invalid_rotation_dates:
            add(
                "rotation.timestamp",
                "warning",
                "Rotation timestamps are not timezone-aware ISO 8601 values for: "
                + ", ".join(invalid_rotation_dates),
            )
        acl_reviewed_at = parse_utc_timestamp(
            rotation_values.get("WINDOWS_ACL_REVIEWED_AT", "")
        )
        if acl_reviewed_at is None:
            add(
                "filesystem.windows_acl",
                "warning",
                "The authoritative Windows ACL review timestamp is missing or invalid.",
            )
        elif acl_reviewed_at > now + timedelta(minutes=5):
            add(
                "filesystem.windows_acl",
                "warning",
                "The authoritative Windows ACL review timestamp is unexpectedly in the future.",
            )
        elif acl_reviewed_at < now - timedelta(days=90):
            add(
                "filesystem.windows_acl",
                "warning",
                "The authoritative Windows ACL review is more than 90 days old.",
            )
        else:
            add(
                "filesystem.windows_acl",
                "pass",
                "Authoritative Windows ACLs have a current, valid review timestamp.",
            )

    failures = sum(item["status"] == "fail" for item in checks)
    warnings = sum(item["status"] == "warning" for item in checks)
    report = {
        "generated_at": datetime.now(UTC).isoformat(),
        "event": "production_secret_audit",
        "status": "failed" if failures else ("warning" if warnings else "passed"),
        "failures": failures,
        "warnings": warnings,
        "checks": checks,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    for item in checks:
        print(f"{item['status'].upper():7} {item['code']}: {item['message']}")
    print(
        f"Secret audit completed with {failures} failure(s) and {warnings} warning(s)."
    )
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
