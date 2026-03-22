# Zenith Architecture

Zenith V1 uses a Python CLI core with a thin shell launcher.

## Layout

- `zenith.sh` bootstraps `PYTHONPATH` and dispatches to `bin/zen`
- `bin/zen` is the direct CLI entrypoint
- `src/zenith/cli.py` owns routing and command semantics
- `src/zenith/install.py` applies core/surface installs and manifest tracking
- `src/zenith/rollback.py` and `src/zenith/manifest.py` own lifecycle recovery
- `src/zenith/ai.py` handles prompt loading, command classification, and audit logging
- `src/zenith/detect.py` resolves package manager, container runtime, GUI state, and mode
- `configs/` stores bash, Zellij, Starship, and Ghostty assets
- `prompts/` stores local AI prompt templates

## State paths

- `~/.config/zenith/zenith.toml` holds the canonical config
- `~/.config/zenith/zenith.bashrc` holds the sourced shell fragment
- `~/.config/zenith/state/` holds `last_command`, `last_status`, `last_stderr`, `last_pwd`, and `session.stderr`
- `~/.local/share/zenith/manifests/` holds install transactions
- `~/.local/share/zenith/backups/` holds file backups for rollback
- `~/.local/share/zenith/audit/` holds AI command audit logs

## Runtime behavior

- shell integration exports `PATH`, initializes Starship and Zoxide when available, and captures command failure context for `zen fix`
- status reporting surfaces shell integration, workspace state, AI provider/model, manifest timestamp, and surface status
- workspace handling uses Zellij when available and reports `ready`, `running`, or `unavailable`
