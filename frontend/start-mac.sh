#!/usr/bin/env bash
#
# Convenience wrapper so the launcher can also be started from frontend/.
# The real implementation lives at the project root.
#
set -uo pipefail
exec "$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/start-mac.sh" "$@"