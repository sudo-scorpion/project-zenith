#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
export PYTHONPATH="$ROOT/src${PYTHONPATH:+:$PYTHONPATH}"

python3 "$ROOT/bin/zen" version >/dev/null
python3 "$ROOT/bin/zen" config validate >/dev/null
python3 "$ROOT/bin/zen" config validate --shell zsh >/dev/null
python3 "$ROOT/bin/zen" status --json >/dev/null
python3 "$ROOT/bin/zen" doctor --json >/dev/null

ROOT="$ROOT" python3 - <<'INNER'
import json
import os
import subprocess
from pathlib import Path

root = Path(os.environ['ROOT'])
status = json.loads(subprocess.check_output(["python3", str(root / "bin/zen"), "status", "--json"], text=True))
assert "container_runtime" in status
assert "distrobox" in status
assert "package_manager" in status
assert "shell_integration" in status
assert "workspace_status" in status
INNER

tmpdir="$(mktemp -d)"
trap 'rm -rf "$tmpdir"' EXIT
mkdir -p "$tmpdir/home" "$tmpdir/config" "$tmpdir/data"

HOME="$tmpdir/home" XDG_CONFIG_HOME="$tmpdir/config" XDG_DATA_HOME="$tmpdir/data" python3 "$ROOT/bin/zen" install core --dry-run --yes >/dev/null
HOME="$tmpdir/home" XDG_CONFIG_HOME="$tmpdir/config" XDG_DATA_HOME="$tmpdir/data" python3 "$ROOT/bin/zen" install core --shell zsh --dry-run --yes >/dev/null
HOME="$tmpdir/home" XDG_CONFIG_HOME="$tmpdir/config" XDG_DATA_HOME="$tmpdir/data" python3 "$ROOT/bin/zen" install all --mode container --dry-run --yes >/dev/null

test ! -e "$tmpdir/config/zenith/zenith.toml"
test ! -e "$tmpdir/data/zenith/manifests/latest.json"
