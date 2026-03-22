# Command Reference

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

## AI assist

- `zen nav "<request>" [--json] [--execute]`
- `zen fix [--json] [--execute]`

`nav` accepts natural-language input and returns a classified command or mini-script. `fix` uses the latest captured failure context when available and falls back to bash or zsh history when it is not.

## Config and metadata

- `zen config show`
- `zen config path`
- `zen config validate`
- `zen config edit`
- `zen version`

`zen config edit` opens the config file in `VISUAL`, `EDITOR`, `nano`, or `vi`.

## Global flags

Most management commands support:

- `--profile safe|personal`
- `--mode auto|host|container`
- `--shell bash|zsh`
- `--dry-run`
- `--yes`
- `--verbose`

`doctor`, `status`, `nav`, and `fix` also support `--json` where applicable.
