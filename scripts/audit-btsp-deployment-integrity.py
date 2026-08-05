#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import subprocess
from datetime import UTC, datetime
from pathlib import Path


DIGEST_PATTERN = re.compile(r"@(?P<digest>sha256:[0-9a-f]{64})$")
EXPECTED_SERVICES = {
    "postgres",
    "redis",
    "backend",
    "frontend",
    "nginx",
    "cloudflared",
}


def run(command: list[str], *, cwd: Path) -> str:
    completed = subprocess.run(
        command,
        cwd=cwd,
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Verify that BTSP production runs the digest-pinned Compose images."
    )
    parser.add_argument("--env-file", default=".env.intranet")
    parser.add_argument("--project", default="btsp-intranet")
    parser.add_argument(
        "--output", default=".runtime/security/deployment-integrity.json"
    )
    args = parser.parse_args()

    root = Path.cwd()
    compose = [
        "docker",
        "compose",
        "--env-file",
        args.env_file,
        "-p",
        args.project,
        "-f",
        "docker-compose.yml",
        "-f",
        "docker-compose.production.yml",
        "-f",
        "docker-compose.intranet.yml",
        "-f",
        "docker-compose.tunnel.yml",
    ]
    checks: list[dict[str, str]] = []

    def add(code: str, status: str, message: str) -> None:
        checks.append({"code": code, "status": status, "message": message})

    try:
        configured_images = {
            line.strip()
            for line in run([*compose, "config", "--images"], cwd=root).splitlines()
            if line.strip()
        }
    except (OSError, subprocess.CalledProcessError):
        configured_images = set()
        add(
            "compose.configuration",
            "fail",
            "The production Compose image configuration could not be rendered.",
        )

    pinned_images: dict[str, str] = {}
    unpinned_count = 0
    for image_reference in configured_images:
        match = DIGEST_PATTERN.search(image_reference)
        if match is None:
            unpinned_count += 1
            continue
        pinned_images[image_reference] = match.group("digest")

    if configured_images and unpinned_count == 0:
        add(
            "compose.image_pins",
            "pass",
            f"All {len(configured_images)} configured service images use immutable SHA-256 digests.",
        )
    elif configured_images:
        add(
            "compose.image_pins",
            "fail",
            f"{unpinned_count} configured service image(s) are not digest-pinned.",
        )

    try:
        container_ids = run(
            [
                "docker",
                "ps",
                "--filter",
                f"label=com.docker.compose.project={args.project}",
                "--format",
                "{{.ID}}",
            ],
            cwd=root,
        ).splitlines()
        inspections = (
            json.loads(run(["docker", "inspect", *container_ids], cwd=root))
            if container_ids
            else []
        )
    except (OSError, subprocess.CalledProcessError, json.JSONDecodeError):
        inspections = []
        add(
            "runtime.inspection",
            "fail",
            "Running production containers could not be inspected.",
        )

    running_services: set[str] = set()
    valid_runtime_images = 0
    for inspection in inspections:
        config = inspection.get("Config", {})
        labels = config.get("Labels") or {}
        service = labels.get("com.docker.compose.service", "")
        if not service:
            continue
        running_services.add(service)
        configured_reference = config.get("Image", "")
        actual_image_id = inspection.get("Image", "")
        expected_digest = pinned_images.get(configured_reference)
        if expected_digest and actual_image_id == expected_digest:
            valid_runtime_images += 1
            add(
                f"runtime.{service}",
                "pass",
                f"The running {service} container matches its configured immutable digest.",
            )
        elif expected_digest:
            add(
                f"runtime.{service}",
                "fail",
                f"The running {service} image does not match its configured digest.",
            )
        else:
            add(
                f"runtime.{service}",
                "fail",
                f"The running {service} container does not use a configured digest-pinned image.",
            )

    missing_services = sorted(EXPECTED_SERVICES - running_services)
    unexpected_services = sorted(running_services - EXPECTED_SERVICES)
    if missing_services:
        add(
            "runtime.services",
            "fail",
            "Required production services are not running: "
            + ", ".join(missing_services),
        )
    elif unexpected_services:
        add(
            "runtime.services",
            "fail",
            "Unexpected services are running in the production project: "
            + ", ".join(unexpected_services),
        )
    elif valid_runtime_images == len(EXPECTED_SERVICES):
        add(
            "runtime.services",
            "pass",
            "The production project contains exactly the six expected services.",
        )

    failures = sum(item["status"] == "fail" for item in checks)
    report = {
        "generated_at": datetime.now(UTC).isoformat(),
        "event": "production_deployment_integrity",
        "status": "failed" if failures else "passed",
        "failures": failures,
        "checks": checks,
    }
    output_path = root / args.output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    for item in checks:
        print(f"{item['status'].upper():7} {item['code']}: {item['message']}")
    print(f"Deployment-integrity audit completed with {failures} failure(s).")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
