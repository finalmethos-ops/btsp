#!/usr/bin/env bash
set -euo pipefail

repository_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repository_root"

"$repository_root/scripts/backup-btsp-production.sh"
"$repository_root/scripts/upload-btsp-production-backup.sh"
