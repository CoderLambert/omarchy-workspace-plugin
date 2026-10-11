#!/usr/bin/env bash
set -euo pipefail
root_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
command -v python3 >/dev/null || { echo '需要 Python 3.11+' >&2; exit 1; }
python3 -c 'import sys; sys.exit(sys.version_info < (3, 11))' || { echo '需要 Python 3.11+' >&2; exit 1; }
exec python3 -B "$root_dir/scripts/install.py" "$@"
