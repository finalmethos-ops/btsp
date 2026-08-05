from __future__ import annotations

import argparse
import os
import re
import tempfile
from pathlib import Path

HOSTNAME_PATTERN = re.compile(
    r"(?=^.{4,253}$)(?!-)(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+"
    r"[a-z](?:[a-z0-9-]{0,61}[a-z0-9])?$"
)


def public_hostname(value: str) -> str:
    hostname = value.strip().lower().rstrip(".")
    if not HOSTNAME_PATTERN.fullmatch(hostname):
        raise argparse.ArgumentTypeError("hostname must be a fully qualified public DNS name")
    return hostname


def update_environment(content: str, hostname: str) -> str:
    public_origin = f"https://{hostname}"
    lines = content.splitlines()
    updated: list[str] = []
    found_cors = False
    found_hostname = False

    for line in lines:
        if line.startswith("CORS_ORIGINS="):
            origins = [
                origin.strip()
                for origin in line.removeprefix("CORS_ORIGINS=").split(",")
                if origin.strip()
            ]
            origins = [origin for origin in origins if origin != public_origin]
            updated.append(f"CORS_ORIGINS={','.join([public_origin, *origins])}")
            found_cors = True
        elif line.startswith("BTSP_PUBLIC_HOSTNAME="):
            updated.append(f"BTSP_PUBLIC_HOSTNAME={hostname}")
            found_hostname = True
        else:
            updated.append(line)

    if not found_cors:
        updated.append(f"CORS_ORIGINS={public_origin}")
    if not found_hostname:
        updated.append(f"BTSP_PUBLIC_HOSTNAME={hostname}")
    return "\n".join(updated) + "\n"


def write_atomically(path: Path, content: str) -> None:
    mode = path.stat().st_mode
    descriptor, temporary_name = tempfile.mkstemp(
        dir=path.parent,
        prefix=f".{path.name}.",
    )
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(content)
        os.chmod(temporary_path, mode)
        temporary_path.replace(path)
    except BaseException:
        temporary_path.unlink(missing_ok=True)
        raise


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Add a public HTTPS hostname to a BTSP environment file."
    )
    parser.add_argument("--hostname", required=True, type=public_hostname)
    parser.add_argument("--environment", default=".env.intranet", type=Path)
    args = parser.parse_args()

    if not args.environment.is_file():
        parser.error(f"environment file does not exist: {args.environment}")
    content = args.environment.read_text(encoding="utf-8")
    write_atomically(args.environment, update_environment(content, args.hostname))
    print(f"Configured BTSP for https://{args.hostname}")


if __name__ == "__main__":
    main()
