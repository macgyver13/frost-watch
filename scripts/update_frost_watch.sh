#!/usr/bin/env bash
set -euo pipefail
cd /Users/gclaw/frost-watch
exec /usr/bin/env python3 scripts/update_frost_watch.py "$@"
