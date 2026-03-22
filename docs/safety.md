# Zenith Safety

Zenith is suggestion-first and rollback-aware.

## AI command policy

- `zen ask` and `zen fix` generate output from local prompt templates
- generated output is classified as `safe`, `review`, or `blocked`
- only `safe` output may run with `--execute`
- even `safe` execution still requires confirmation
- `review` and `blocked` output is never auto-run by Zenith V1

## Install safety

- managed files are backed up before Zenith rewrites them
- `install --dry-run` previews work without writing config or manifests
- `surface` is gated behind host mode
- without a GUI session, Zenith skips only the GUI-facing surface assets
- `install all` skips surface cleanly outside host mode and fails clearly when a requested host terminal cannot be installed

## Auditability

- AI-generated commands are logged under `~/.local/share/zenith/audit/`
- manifests are append-only transaction records under `~/.local/share/zenith/manifests/`
- rollback consumes manifest plus backup history rather than guessing what Zenith changed
