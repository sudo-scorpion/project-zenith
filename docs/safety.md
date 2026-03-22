# Zenith Safety

Zenith is suggestion-first and rollback-aware.

## AI command policy

- `zen nav` and `zen fix` generate output from local prompt templates
- generated output is classified as `safe`, `review`, or `blocked`
- only `safe` output may run with `--execute`
- even `safe` execution still requires confirmation
- `review` and `blocked` output is never auto-run by Zenith V1

## Install safety

- managed files are backed up before Zenith rewrites them
- `install --dry-run` previews work without writing config or manifests
- `surface` is gated behind host mode and GUI detection
- `install all` skips surface cleanly when host-only requirements are unavailable

## Auditability

- AI-generated commands are logged under `~/.local/share/zenith/audit/`
- manifests are append-only transaction records under `~/.local/share/zenith/manifests/`
- rollback consumes manifest plus backup history rather than guessing what Zenith changed
