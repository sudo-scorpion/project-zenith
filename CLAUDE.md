# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Zenith is a container-aware terminal platform with a unified CLI (`zen`) for AI-assisted shell setup and management. Zero external Python dependencies — pure Python 3.11+.

**Two-layer architecture:**
- **Core** (portable): Shell integration, AI helpers (Ollama), workspace (Zellij), status, rollback
- **Surface** (host-only): Terminal config (Kitty/Ghostty), orbit theme shaders, fonts

**Three deployment modes:** hybrid (host CLI + Podman container), host-only, container-only.

## Build & Test Commands

```bash
# Install (editable for dev)
pip install -e .

# Compile check
python -m py_compile src/zenith/*.py bin/zen

# Smoke tests (quick)
bash tests/smoke/router.sh

# Integration tests (full lifecycle)
bash tests/integration/lifecycle.sh

# Packaged install tests
bash tests/integration/package_install.sh
```

Tests are shell scripts, not pytest. CI runs on Ubuntu with Python 3.11.

## CLI Entry Point

`zenith.cli:main()` — argparse-based router. Both `zen` and `zenith` console_scripts point here.

Key commands: `install {core|surface|all}`, `uninstall`, `rollback`, `doctor`, `status`, `ask`, `fix`, `agent`, `orbit`, `config`, `upgrade surface`, `workspace`, `shell`, `context`, `models`, `plugins`, `theme`.

## Architecture

| Module | Role |
|--------|------|
| `cli.py` | Argparse router, shell default behavior |
| `install.py` | Core/surface installation, package management, binary downloads |
| `ai.py` | Ollama integration, prompt templates, command safety classification |
| `agent.py` | Multi-step AI agent: generates a plan via structured JSON, executes each shell step with safety classification, aborts if LLM signals danger |
| `context.py` | Session context persistence — current task, project root (auto-detected via markers), recent errors — stored at `~/.local/share/zenith/context.json` |
| `model_manager.py` | Per-task Ollama model selection (`ask`/`fix`/`agent`); reads `[ai.models]` table first, falls back to legacy `ask_model`/`fix_model` keys, then `model` |
| `plugins.py` | Python plugin loader from `~/.config/zenith/plugins/*.py`; each plugin exposes `COMMAND`, `DESCRIPTION`, and `run(args, config, paths)` |
| `theme.py` | Theme management — built-in orbit themes + user TOML themes from `~/.config/zenith/themes/`; applies colors to Kitty via `surface.py` |
| `config.py` | TOML config loading/validation, defaults, profiles |
| `detect.py` | Distro, package manager, container runtime detection |
| `doctor.py` | Health checks with structured JSON output |
| `status.py` | Runtime status reporting |
| `updates.py` | Version tracking, upgrade scheduling |
| `rollback.py` | Transaction rollback from manifests |
| `manifest.py` | Timestamped JSON install manifests |
| `backup.py` | File backup into timestamped dirs under `~/.local/share/zenith/backups/` during installs |
| `binaries.py` | Binary resolution (`shutil.which` + `~/.local/bin`) |
| `paths.py` | XDG-compliant path builder |
| `shells.py` | Shell detection/normalization, fragment paths |
| `surface.py` | Ghostty/Kitty orbit theme application |
| `models.py` | Dataclass definitions |

## Key Design Constraints

- **No hardcoded sudo in Python code** — `zen install core` stays in user space by default; sudo is only used when the user explicitly passes `--packages` (which `./bootstrap.sh host` does automatically for system package installs)
- **XDG-compliant** — config in `~/.config/zenith`, data in `~/.local/share/zenith`
- **Transactional installs** — every install creates a JSON manifest enabling atomic rollback
- **Command safety classification** in `ai.py`: safe (ls, grep), review (sudo, dnf), blocked (rm -rf, mkfs)
- **Fail-fast bootstrap** — won't claim success if Ollama model or tools are missing
- **Shell support**: bash and zsh only (normalized in `shells.py`)
- **Fatal errors**: use `raise SystemExit(message)`, not `sys.exit()`
- **Logging**: use `logging_utils` functions (`info`, `warn`, `note`, `ok`, `fail`)

## Config

TOML at `~/.config/zenith/zenith.toml`. Sections: profile, mode, features, ai, surface, updates, workspace, paths. Validated by `config.py`.

## Environment Variables

- `ZENITH_PROFILE` — safe/personal profile override
- `ZENITH_CONTAINER_NAME` / `ZENITH_IMAGE_NAME` — container identity
- `ZENITH_TERMINAL` — kitty/ghostty preference
- `ZENITH_CONTAINER_GPU` — auto/nvidia/none

## Assets

Bundled under `src/zenith/assets/`: shell configs (bash, zsh), starship config, zellij layouts, terminal configs (kitty, ghostty with orbit shaders), and AI prompt templates. Included in wheel via `pyproject.toml` package-data.
