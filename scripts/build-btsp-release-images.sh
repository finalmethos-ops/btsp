#!/usr/bin/env bash
set -euo pipefail

repository_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repository_root"

version="${BTSP_RELEASE_VERSION:-}"
registry="${BTSP_RELEASE_REGISTRY:-ghcr.io/finalmethos-ops}"
public_api_base_url="${BTSP_RELEASE_PUBLIC_API_BASE_URL:-}"
output_directory="${BTSP_RELEASE_OUTPUT_DIRECTORY:-.runtime/releases}"

if [[ ! "$version" =~ ^v?[0-9]+\.[0-9]+\.[0-9]+(-rc\.[0-9]+)?$ ]]; then
  echo "Set BTSP_RELEASE_VERSION to a semantic release such as v1.0.0-rc.23." >&2
  exit 2
fi
if [[ -n "$(git status --porcelain=v1)" ]]; then
  echo "Release images must be built from a clean reviewed Git worktree." >&2
  exit 3
fi

revision="$(git rev-parse HEAD)"
created_at="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
backend_image="${registry}/btsp-backend:${version}"
frontend_image="${registry}/btsp-frontend:${version}"

echo "Building BTSP release images from revision $revision."
docker build \
  --build-arg INSTALL_DEV_DEPS=false \
  --build-arg "BUILD_VERSION=$version" \
  --build-arg "BUILD_REVISION=$revision" \
  --build-arg "BUILD_CREATED=$created_at" \
  --tag "$backend_image" \
  backend
docker build \
  --build-arg "NEXT_PUBLIC_API_BASE_URL=$public_api_base_url" \
  --build-arg "BUILD_VERSION=$version" \
  --build-arg "BUILD_REVISION=$revision" \
  --build-arg "BUILD_CREATED=$created_at" \
  --tag "$frontend_image" \
  frontend

for image in "$backend_image" "$frontend_image"; do
  image_revision="$(
    docker image inspect --format '{{index .Config.Labels "org.opencontainers.image.revision"}}' "$image"
  )"
  image_version="$(
    docker image inspect --format '{{index .Config.Labels "org.opencontainers.image.version"}}' "$image"
  )"
  if [[ "$image_revision" != "$revision" || "$image_version" != "$version" ]]; then
    echo "Release provenance labels are invalid for $image." >&2
    exit 4
  fi
done

backend_id="$(docker image inspect --format '{{.Id}}' "$backend_image")"
frontend_id="$(docker image inspect --format '{{.Id}}' "$frontend_image")"
mkdir -p "$output_directory"
manifest_path="$output_directory/${version}-manifest.json"
python3 - \
  "$manifest_path" \
  "$version" \
  "$revision" \
  "$created_at" \
  "$backend_image" \
  "$backend_id" \
  "$frontend_image" \
  "$frontend_id" <<'PY'
import json
import sys
from pathlib import Path

(
    output,
    version,
    revision,
    created_at,
    backend_image,
    backend_id,
    frontend_image,
    frontend_id,
) = sys.argv[1:]
manifest = {
    "version": version,
    "source_revision": revision,
    "created_at": created_at,
    "images": {
        "backend": {"reference": backend_image, "local_id": backend_id},
        "frontend": {"reference": frontend_image, "local_id": frontend_id},
    },
}
Path(output).write_text(
    json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
)
PY

echo "Release images built and provenance-verified."
echo "Manifest: $manifest_path"
echo "Publishing and production promotion remain separate approved actions."
