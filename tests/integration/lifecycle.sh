#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
export PYTHONPATH="$ROOT/src${PYTHONPATH:+:$PYTHONPATH}"

scenario_one="$(mktemp -d)"
scenario_two="$(mktemp -d)"
scenario_three="$(mktemp -d)"
scenario_four="$(mktemp -d)"
trap 'rm -rf "$scenario_one" "$scenario_two" "$scenario_three" "$scenario_four"' EXIT

mkdir -p "$scenario_one/home" "$scenario_one/config" "$scenario_one/data"
printf 'export ORIGINAL_SHELL=1
' > "$scenario_one/home/.bashrc"

HOME="$scenario_one/home" XDG_CONFIG_HOME="$scenario_one/config" XDG_DATA_HOME="$scenario_one/data" python3 "$ROOT/bin/zen" install core --mode host --profile personal --yes >/dev/null

test -f "$scenario_one/config/zenith/zenith.toml"
grep -q '\[paths\]' "$scenario_one/config/zenith/zenith.toml"
grep -q 'install_root' "$scenario_one/config/zenith/zenith.toml"
grep -q 'alias ls=' "$scenario_one/config/zenith/zenith.bashrc"
grep -q '__zenith_preexec' "$scenario_one/config/zenith/zenith.bashrc"
grep -q '# Project Zenith' "$scenario_one/home/.bashrc"
test -f "$scenario_one/data/zenith/manifests/latest.json"

HOME="$scenario_one/home" XDG_CONFIG_HOME="$scenario_one/config" XDG_DATA_HOME="$scenario_one/data" ROOT="$ROOT" python3 - <<'INNER'
import json
import os
import subprocess
from pathlib import Path

root = Path(os.environ['ROOT'])
status = json.loads(subprocess.check_output([
    "python3",
    str(root / "bin/zen"),
    "status",
    "--mode",
    "host",
    "--json",
], text=True, env=os.environ.copy()))
assert status["components"]["core"] is True
assert status["shell_integration"] == "configured"
assert status["latest_manifest_timestamp"]
assert status["workspace_status"] in {"ready", "running", "unavailable"}
INNER

printf 'badcmd
' > "$scenario_one/config/zenith/state/last_command"
printf '2
' > "$scenario_one/config/zenith/state/last_status"
printf 'ls: cannot access nope
' > "$scenario_one/config/zenith/state/last_stderr"
printf '%s
' "$scenario_one/home" > "$scenario_one/config/zenith/state/last_pwd"

HOME="$scenario_one/home" XDG_CONFIG_HOME="$scenario_one/config" XDG_DATA_HOME="$scenario_one/data" ROOT="$ROOT" python3 - <<'INNER'
import os
from pathlib import Path

from zenith.ai import read_fix_context
from zenith.paths import build_paths

paths = build_paths(Path(os.environ['ROOT']))
context = read_fix_context(paths)
assert context["command"] == "badcmd"
assert context["exit_status"] == 2
assert "cannot access" in str(context["stderr"])
INNER

HOME="$scenario_one/home" XDG_CONFIG_HOME="$scenario_one/config" XDG_DATA_HOME="$scenario_one/data" python3 "$ROOT/bin/zen" rollback >/dev/null

grep -q '^export ORIGINAL_SHELL=1$' "$scenario_one/home/.bashrc"
test ! -e "$scenario_one/config/zenith/zenith.toml"
test ! -e "$scenario_one/data/zenith/manifests/latest.json"

mkdir -p "$scenario_two/home" "$scenario_two/config" "$scenario_two/data"
HOME="$scenario_two/home" XDG_CONFIG_HOME="$scenario_two/config" XDG_DATA_HOME="$scenario_two/data" python3 "$ROOT/bin/zen" install core --mode host --yes >/dev/null
HOME="$scenario_two/home" XDG_CONFIG_HOME="$scenario_two/config" XDG_DATA_HOME="$scenario_two/data" python3 "$ROOT/bin/zen" uninstall >/dev/null

test ! -e "$scenario_two/home/.bashrc"
test ! -d "$scenario_two/config/zenith"
test ! -d "$scenario_two/data/zenith"

mkdir -p "$scenario_three/home" "$scenario_three/config" "$scenario_three/data"
HOME="$scenario_three/home" XDG_CONFIG_HOME="$scenario_three/config" XDG_DATA_HOME="$scenario_three/data" python3 "$ROOT/bin/zen" install all --mode container --yes >/dev/null

test -f "$scenario_three/config/zenith/zenith.toml"
test ! -e "$scenario_three/home/.config/ghostty/config"
HOME="$scenario_three/home" XDG_CONFIG_HOME="$scenario_three/config" XDG_DATA_HOME="$scenario_three/data" ROOT="$ROOT" python3 - <<'INNER'
import json
import os
import subprocess
from pathlib import Path

root = Path(os.environ['ROOT'])
status = json.loads(subprocess.check_output([
    "python3",
    str(root / "bin/zen"),
    "status",
    "--mode",
    "container",
    "--json",
], text=True, env=os.environ.copy()))
assert status["components"]["core"] is True
assert status["components"]["surface"] is False
assert status["surface_status"] == "absent"
INNER

mkdir -p "$scenario_four/home" "$scenario_four/config" "$scenario_four/data"
printf ': 1712345678:0;broken zsh command
' > "$scenario_four/home/.zsh_history"
HOME="$scenario_four/home" XDG_CONFIG_HOME="$scenario_four/config" XDG_DATA_HOME="$scenario_four/data" python3 "$ROOT/bin/zen" install core --mode host --shell zsh --yes >/dev/null

test -f "$scenario_four/config/zenith/zenith.zshrc"
grep -q '__zenith_preexec' "$scenario_four/config/zenith/zenith.zshrc"
grep -q '# Project Zenith' "$scenario_four/home/.zshrc"
HOME="$scenario_four/home" XDG_CONFIG_HOME="$scenario_four/config" XDG_DATA_HOME="$scenario_four/data" ROOT="$ROOT" python3 - <<'INNER'
import os
from pathlib import Path

from zenith.ai import _latest_history_command
from zenith.paths import build_paths

paths = build_paths(Path(os.environ['ROOT']))
command = _latest_history_command(paths, 'zsh')
assert command == 'broken zsh command'
INNER
