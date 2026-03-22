#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
tmpdir="$(mktemp -d)"
trap 'rm -rf "$tmpdir"' EXIT

python3 -m venv "$tmpdir/venv"
"$tmpdir/venv/bin/pip" install --no-cache-dir "$ROOT" >/dev/null

mkdir -p "$tmpdir/home" "$tmpdir/config" "$tmpdir/data"
HOME="$tmpdir/home" XDG_CONFIG_HOME="$tmpdir/config" XDG_DATA_HOME="$tmpdir/data" "$tmpdir/venv/bin/zen" install core --mode host --shell zsh --yes >/dev/null

test -f "$tmpdir/config/zenith/zenith.toml"
test -f "$tmpdir/config/zenith/zenith.zshrc"
test -f "$tmpdir/config/zenith/prompts/nav.prompt"
grep -q '# Project Zenith' "$tmpdir/home/.zshrc"
test -f "$tmpdir/data/zenith/manifests/latest.json"

HOME="$tmpdir/home" XDG_CONFIG_HOME="$tmpdir/config" XDG_DATA_HOME="$tmpdir/data" "$tmpdir/venv/bin/zen" rollback >/dev/null

test ! -e "$tmpdir/config/zenith/zenith.toml"
test ! -e "$tmpdir/data/zenith/manifests/latest.json"
