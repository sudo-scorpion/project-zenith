# Command Reference

For most users, only these commands matter:

- setup: `./bootstrap.sh host --terminal kitty`
- cleanup: `./teardown.sh host`
- fresh reset: `./bootstrap.sh host --fresh --terminal kitty`
- daily use: `ai "request"` and `fix`

Everything below is the full command reference.

## Shell shortcuts (available after `zen install core`)

These are shell functions installed into your zsh/bash session — no `zen` prefix needed:

- `ai "<request>"` — ask a question, get a terminal command back (alias for `zen ask`)
- `fix` — analyze the last failed command and suggest a fix (alias for `zen fix`)

## Main User Commands

- `zen install core [--packages]`
- `zen install surface`
- `zen install all [--packages]`
- `zen uninstall`
- `zen rollback`
- `zen doctor [--json]`
- `zen status [--json]`
- `zen upgrade surface`
- `zen upgrade surface --check [--json]`
- `zen workspace`
- `zen ask "<request>" [--json] [--execute]`
- `zen nav "<request>" [--json] [--execute]` alias for `zen ask`
- `zen fix [--json] [--execute]`
- `zen config show`
- `zen config edit`
- `zen version`

## Internal Or Developer-Facing Scripts

These are not the commands a normal end user needs to memorize:

- `bootstrap.sh`: top-level setup wrapper, including `fresh` reinstall mode, `--terminal`, `--gpu auto|nvidia|none`
- `teardown.sh`: top-level cleanup wrapper, including `clean` alias
- `zenith.sh`: repo-local development runner
- `bin/zen`: packaged CLI entrypoint implementation
- `tests/smoke/router.sh`: smoke verification
- `tests/integration/lifecycle.sh`: lifecycle verification
- `tests/integration/package_install.sh`: package-install verification

## Lifecycle

- `zen install core [--packages]` — install core tools and shell integration
- `zen install surface` — install terminal surface assets
- `zen install all [--packages]` — install core then surface
- `zen uninstall` — revert all transactions, remove Zenith config
- `zen rollback` — revert the latest transaction only
- `zen doctor [--json]` — health check
- `zen status [--json]` — runtime state
- `zen upgrade surface` — install or upgrade the configured terminal
- `zen upgrade surface --check [--json]` — check whether an upgrade is available

## Runtime

- `zen workspace` — open the Zellij workspace session
- `zen orbit <celestial|matrix|quantum|void>` — apply Ghostty orbit theme
- `zen sync`

## AI Assist

- `ai "<request>"` — shell shortcut for `zen ask`
- `fix` — shell shortcut for `zen fix`
- `zen ask "<request>" [--json] [--execute]`
- `zen nav "<request>" [--json] [--execute]` alias for `zen ask`
- `zen fix [--json] [--execute]`

`ask` accepts natural-language input and returns a classified command or mini-script. `fix` uses the latest captured failure context (stderr, exit code, last command) when available and falls back to shell history when it is not.

## Config And Metadata

- `zen config show`
- `zen config path`
- `zen config validate`
- `zen config edit` — opens config in `VISUAL`, `EDITOR`, `nano`, or `vi`
- `zen upgrade surface`
- `zen upgrade surface --check [--json]`
- `zen version`

## Global Flags

Most management commands support:

- `--profile safe|personal`
- `--mode auto|host|container`
- `--shell bash|zsh`
- `--terminal NAME`: request a host user-space install for that terminal; `kitty` is the default
- `--packages`: enable system package manager installs with `sudo` (host mode only)
- `--dry-run`
- `--yes`
- `--verbose`

`doctor`, `status`, `ask`, and `fix` also support `--json` where applicable.
