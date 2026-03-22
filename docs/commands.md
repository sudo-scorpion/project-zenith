# Command Reference

For most users, only three commands matter:

- setup: `./bootstrap.sh`
- cleanup: `./teardown.sh`
- fresh reset: `./bootstrap.sh fresh`
- daily use: `zen`

Everything below is the advanced command reference for people who want to operate Zenith directly.

## Main User Commands

- `zen install core`
- `zen install surface`
- `zen install all`
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

- `bootstrap.sh`: top-level setup wrapper, including `fresh` reinstall mode, `--terminal`, and `--gpu auto|nvidia|none`
- `teardown.sh`: top-level cleanup wrapper, including `clean` alias
- `zenith.sh`: repo-local development runner
- `bin/zen`: packaged CLI entrypoint implementation
- `tests/smoke/router.sh`: smoke verification
- `tests/integration/lifecycle.sh`: lifecycle verification
- `tests/integration/package_install.sh`: package-install verification

## Lifecycle

- `zen install core`
- `zen install surface`
- `zen install all`
- `zen uninstall`
- `zen rollback`
- `zen doctor [--json]`
- `zen status [--json]`
- `zen upgrade surface`
- `zen upgrade surface --check [--json]`

## Runtime

- `zen workspace`
- `zen orbit <celestial|matrix|quantum|void>`
- `zen sync`

## AI Assist

- `zen ask "<request>" [--json] [--execute]`
- `zen nav "<request>" [--json] [--execute]` alias for `zen ask`
- `zen fix [--json] [--execute]`

`ask` accepts natural-language input and returns a classified command or mini-script. `zen nav` remains as a compatibility alias. `fix` uses the latest captured failure context when available and falls back to bash or zsh history when it is not.

## Config And Metadata

- `zen config show`
- `zen config path`
- `zen config validate`
- `zen config edit`
- `zen upgrade surface`
- `zen upgrade surface --check [--json]`
- `zen version`

`zen config edit` opens the config file in `VISUAL`, `EDITOR`, `nano`, or `vi`. `zen upgrade surface --check` reports the installed surface version, recommended version, and whether Zenith thinks an install or upgrade is available. `zen upgrade surface` applies that install or upgrade in user space for supported terminals.

## Global Flags

Most management commands support:

- `--profile safe|personal`
- `--mode auto|host|container`
- `--shell bash|zsh`
- `--terminal NAME`: request a host user-space install for that terminal when Zenith knows how; `kitty` is the default supported path
- `--gpu auto|nvidia|none`: control Podman container GPU passthrough during bootstrap
- `--dry-run`
- `--yes`
- `--verbose`

`doctor`, `status`, `ask`, and `fix` also support `--json` where applicable.
