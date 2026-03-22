# Command Reference

For most users, only three commands matter:

- setup: `./bootstrap.sh`
- cleanup: `./teardown.sh`
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
- `zen workspace`
- `zen nav "<request>" [--json] [--execute]`
- `zen fix [--json] [--execute]`
- `zen config show`
- `zen config edit`
- `zen version`

## Internal Or Developer-Facing Scripts

These are not the commands a normal end user needs to memorize:

- `bootstrap.sh`: top-level setup wrapper
- `teardown.sh`: top-level cleanup wrapper
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

## Runtime

- `zen workspace`
- `zen orbit <celestial|matrix|quantum|void>`
- `zen sync`

## AI Assist

- `zen nav "<request>" [--json] [--execute]`
- `zen fix [--json] [--execute]`

`nav` accepts natural-language input and returns a classified command or mini-script. `fix` uses the latest captured failure context when available and falls back to bash or zsh history when it is not.

## Config And Metadata

- `zen config show`
- `zen config path`
- `zen config validate`
- `zen config edit`
- `zen version`

`zen config edit` opens the config file in `VISUAL`, `EDITOR`, `nano`, or `vi`.

## Global Flags

Most management commands support:

- `--profile safe|personal`
- `--mode auto|host|container`
- `--shell bash|zsh`
- `--dry-run`
- `--yes`
- `--verbose`

`doctor`, `status`, `nav`, and `fix` also support `--json` where applicable.
